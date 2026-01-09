import os
import re
import shutil
import urllib.parse
import yt_dlp
import requests
import speech_recognition as sr
from pydub import AudioSegment
from pathlib import Path
from dotenv import load_dotenv

# LangChain Imports
from langchain_core.documents import Document
from langchain_community.document_loaders import WikipediaLoader, WebBaseLoader, PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# DB Import
from backend.db.milvus_handler import insert_vectors

# ==========================================
# 1. ROBUST ENV LOADING & SETUP
# ==========================================
# Automatically find the 'backend' folder to locate .env
current_file_path = Path(__file__).resolve()
backend_dir = current_file_path.parent.parent  # Go up two levels: services -> backend
env_path = backend_dir / ".env"

# Load the .env file explicitly
load_dotenv(dotenv_path=env_path)

# Debug check
api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    # Fallback: Try loading from current working directory just in case
    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    print(f"❌ CRITICAL ERROR: TAVILY_API_KEY is missing!")
    print(f"   Checked path: {env_path}")
    print("   Please ensure 'TAVILY_API_KEY' is set in your backend/.env file.")
else:
    print(f"✅ TAVILY_API_KEY found (starts with: {api_key[:5]}...)")

# Import Tavily (Handle both new and old versions)
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults

print("📥 Loading Embedding Model...")
embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Initialize Search Tool with EXPLICIT key to fix Pydantic error
search_tool = TavilySearchResults(
    k=10,
    tavily_api_key=api_key  # <--- THIS IS THE KEY FIX
)

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# ==========================================
# 2. CHUNKING & EMBEDDING PIPELINE
# ==========================================
def text_chunk_pipeline(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)

def embed_text(chunks):
    return embedder.embed_documents(chunks)

def embed_query(text):
    return embedder.embed_query(text)

def run_ingestion_pipeline(docs):
    """
    Takes a LIST of documents, chunks them, embeds them, and stores in Milvus.
    """
    if not docs: 
        return 0
    
    total_chunks = 0
    print(f"\n🚀 STARTING INGESTION for {len(docs)} document(s)...")
    
    for i, doc in enumerate(docs):
        source_name = doc.metadata.get('source', 'Unknown')
        title = doc.metadata.get('title', 'Untitled')
        print(f"   📄 Processing: {title} ({source_name})")
        
        # 1. Chunk
        chunks = text_chunk_pipeline(doc.page_content)
        
        if chunks:
            # 2. Embed
            vectors = embed_text(chunks)
            
            # 3. Store to Milvus
            insert_vectors(chunks, vectors, source_name)
            
            total_chunks += len(chunks)
            print(f"      ✅ Generated & Stored {len(vectors)} chunks.")
    
    return total_chunks

# ==========================================
# 3. DIRECT LOADING FUNCTIONS
# ==========================================
def clean_vtt_text(vtt_content):
    lines = vtt_content.split('\n')
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('WEBVTT') or '-->' in line: continue
        line = re.sub(r'<[^>]+>', '', line)
        if text_lines and text_lines[-1] == line: continue
        text_lines.append(line)
    return " ".join(text_lines)

def load_audio(file_path):
    print(f"🎤 Processing Audio File: {file_path}")
    if not os.path.exists(file_path): return None

    try:
        audio = AudioSegment.from_file(file_path)
        wav_path = file_path + ".wav"
        audio.export(wav_path, format="wav")
        
        recognizer = sr.Recognizer()
        text = ""
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
            except sr.UnknownValueError:
                text = "[Audio Unintelligible]"
            except sr.RequestError as e:
                text = f"[API Error: {e}]"
        
        if os.path.exists(wav_path): os.remove(wav_path)

        return Document(
            page_content=text, 
            metadata={"source": os.path.basename(file_path), "type": "audio", "title": os.path.basename(file_path)}
        )
    except Exception as e:
        print(f"❌ Audio Error: {e}")
        return None

def load_youtube(url):
    print(f"🎥 Detected YouTube URL: {url}")
    ydl_opts = {'skip_download': True, 'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['en'], 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            subtitles = info.get('requested_subtitles')
            if not subtitles or 'en' not in subtitles: return None
            
            response = requests.get(subtitles['en']['url'])
            transcript_text = ""
            try:
                data = response.json()
                for event in data.get('events', []):
                    for seg in event.get('segs', []):
                        if 'utf8' in seg and seg['utf8'] != '\n': transcript_text += seg['utf8']
            except ValueError:
                transcript_text = clean_vtt_text(response.text)

            return Document(page_content=transcript_text.strip(), metadata={"source": url, "title": title, "type": "youtube"})
    except Exception:
        return None

def load_wikipedia(url):
    print(f"📚 Detected Wikipedia URL: {url}")
    try:
        topic = urllib.parse.unquote(urllib.parse.urlparse(url).path.split("/")[-1])
        docs = WikipediaLoader(query=topic, load_max_docs=1, doc_content_chars_max=10000).load()
        if docs:
            docs[0].metadata["type"] = "wikipedia"
            return docs[0]
    except Exception:
        return None

def load_website(url):
    print(f"🌐 Detected General Website: {url}")
    try:
        docs = WebBaseLoader(url).load()
        if docs:
            docs[0].page_content = " ".join(docs[0].page_content.strip().split())
            docs[0].metadata["type"] = "website"
            return docs[0]
    except Exception:
        return None

def load_local_file(file_path):
    """Handles local PDF/TXT uploads from Streamlit"""
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        full_text = "\n".join([d.page_content for d in docs])
        return Document(page_content=full_text, metadata={"source": os.path.basename(file_path)})
    
    elif file_path.endswith((".txt", ".md", ".py")):
        loader = TextLoader(file_path)
        return loader.load()[0]
    
    return None

# ==========================================
# 4. MAIN PROCESSORS (API CALLED)
# ==========================================

def process_direct_url(url: str):
    """Handles URL ingestion (YouTube, Wiki, Web)."""
    doc = None
    if "youtube.com" in url or "youtu.be" in url:
        doc = load_youtube(url)
    elif "wikipedia.org" in url:
        doc = load_wikipedia(url)
    elif url.startswith("http"):
        doc = load_website(url)
    
    if doc:
        return run_ingestion_pipeline([doc])
    return 0

def process_topic_search_api(topic: str):
    """
    Backend version of 'process_topic_search'.
    Searches Tavily, picks top 5 results, scrapes, and ingests them automatically.
    """
    print(f"\n🔎 API Searching web for: '{topic}'...")
    try:
        # Pass query explicitly
        results = search_tool.invoke({"query": topic})
        
        # Depending on version, results might be a list or dict. Handle safely:
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
            
        urls = [r["url"] for r in results if "url" in r]
        
        # Deduplicate and limit to top 5
        urls = list(dict.fromkeys(urls))[:5]
        
        if not urls:
            return 0
            
        print(f"   📄 Scraping {len(urls)} URLs...")
        loader = WebBaseLoader(urls)
        docs = loader.load()
        
        return run_ingestion_pipeline(docs)
        
    except Exception as e:
        print(f"❌ Search Error: {e}")
        return 0

async def process_uploaded_file_api(file):
    """
    Handles physical file uploads (PDF, TXT, Audio) from Streamlit.
    """
    file_path = os.path.join(TEMP_DIR, file.filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        doc = None
        
        # Audio check
        if file.filename.endswith((".mp3", ".wav", ".m4a")):
            doc = load_audio(file_path)
        else:
            # Standard docs
            doc = load_local_file(file_path)
            
        if doc:
            return run_ingestion_pipeline([doc])
        return 0
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)