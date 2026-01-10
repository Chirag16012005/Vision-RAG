import os
import re
import shutil
import traceback  # <--- CRITICAL FOR DEBUGGING
import urllib.parse
import yt_dlp
import base64
import uuid
import glob
import speech_recognition as sr
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import requests
import numpy as np
from pydub import AudioSegment

# --- LANGCHAIN IMPORTS ---
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    WebBaseLoader, TextLoader, CSVLoader, UnstructuredMarkdownLoader, NotebookLoader
)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, PythonCodeTextSplitter

# --- DB IMPORT ---
from backend.db.milvus_handler import insert_vectors

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
print("🔄 Initializing Ingestion Service...")

current_file_path = Path(__file__).resolve()
backend_dir = current_file_path.parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

os.environ["USER_AGENT"] = "RAG_Assistant/1.0"

# Directories
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)
IMAGE_OUTPUT_DIR = os.path.join(os.getcwd(), "extracted_images")
os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

# API Keys
api_key = os.getenv("TAVILY_API_KEY")

# Search Tool
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults

# Initialize Search Tool
if api_key:
    search_tool = TavilySearchResults(max_results=20, tavily_api_key=api_key)
else:
    print("⚠️ Tavily API Key missing. Search will fail.")
    search_tool = None

# Embeddings
print("📥 Loading Embedding Model...")
try:
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("✅ Models Ready.")
except Exception as e:
    print(f"❌ Failed to load embedding model: {e}")
    embedder = None

# ==========================================
# 2. CHUNKING PIPELINE
# ==========================================
def text_chunk_pipeline(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text)

def embed_text(chunks):
    if not embedder:
        raise ValueError("Embedding model is not loaded.")
    return embedder.embed_documents(chunks)

def embed_query(text):
    if not embedder:
        raise ValueError("Embedding model is not loaded.")
    return embedder.embed_query(text)

def clean_vtt_content(vtt_text):
    """
    Cleans WebVTT subtitle formatting to get raw human text.
    """
    lines = vtt_text.split('\n')
    cleaned_lines = []
    seen_lines = set()
    for line in lines:
        if '-->' in line or line.strip() == '' or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        if clean_line and clean_line not in seen_lines:
            cleaned_lines.append(clean_line)
            seen_lines.add(clean_line)
    return " ".join(cleaned_lines)

def load_youtube(url):
    print(f"🎥 Downloading YouTube Subs via yt-dlp: {url}")
    file_id = f"yt_{uuid.uuid4().hex[:8]}"
    output_template = os.path.join(TEMP_DIR, f"{file_id}")
    
    ydl_opts = {
        'skip_download': True,      
        'writeautomaticsub': True,  
        'subtitleslangs': ['en'],   
        'subtitlesformat': 'vtt',   
        'outtmpl': output_template, 
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'YouTube Video')
            author = info.get('uploader', 'Unknown')
        
        # Find the downloaded file
        downloaded_files = glob.glob(os.path.join(TEMP_DIR, f"{file_id}*.vtt"))
        
        if not downloaded_files:
            print("⚠️ No subtitles found.")
            return None
            
        vtt_path = downloaded_files[0]
        with open(vtt_path, 'r', encoding='utf-8') as f:
            raw_vtt = f.read()
            
        clean_text = clean_vtt_content(raw_vtt)
        if os.path.exists(vtt_path): os.remove(vtt_path)
            
        if not clean_text: return None

        print(f"✅ Success! Extracted {len(clean_text)} chars.")
        # Source becomes the URL, so collection will be based on sanitizing this URL
        return Document(
            page_content=clean_text,
            metadata={"source": url, "title": title, "author": author, "type": "youtube"}
        )

    except Exception as e:
        print(f"❌ YouTube Error: {e}")
        return None

# ==========================================
# 6. OTHER STANDARD LOADERS
# ==========================================
def load_audio(file_path):
    print(f"🎤 Processing Audio: {file_path}")
    try:
        audio = AudioSegment.from_file(file_path)
        wav_path = file_path + ".wav"
        audio.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try: text = recognizer.recognize_google(audio_data)
            except: text = "[Unintelligible]"
        if os.path.exists(wav_path): os.remove(wav_path)
        return Document(page_content=text, metadata={"source": os.path.basename(file_path), "type": "audio", "title": os.path.basename(file_path)})
    except: return None

def load_website(url):
    try: return WebBaseLoader(url).load()[0]
    except: return None

def run_ingestion_pipeline(docs):
    """
    Main loop to process documents and insert into Milvus.
    Wrapped in try/except to prevent 500 Errors.
    """
    if not docs: return 0
    total_chunks = 0
    print(f"\n🚀 STARTING INGESTION for {len(docs)} document(s)...")
    
    for i, doc in enumerate(docs):
        try:
            # 1. Identify the "Bucket" (Filename/Source)
            source_name = doc.metadata.get('source', 'Unknown_Source')
            title = doc.metadata.get('title', 'Untitled')
            doc_type = doc.metadata.get('type', 'generic')
            
            print(f"   📄 Processing: {title} ({doc_type})")
            
            # 2. Prepare Content
            chunks = []
            if doc_type in ['image', 'table']:
                # Images are kept as single blocks
                chunks = [doc.page_content]
            else:
                # Text is chunked
                content = str(doc.page_content)
                if len(content) > 2000:
                    chunks = text_chunk_pipeline(content)
                else:
                    chunks = [content]
            
            if chunks:
                # 3. Embed chunks
                # This might fail if the model crashed, so we catch it
                vectors = embed_text(chunks)
                
                # 4. Replicate metadata for each chunk
                metas = [doc.metadata] * len(chunks)
                
                # 5. Insert into the FILE-SPECIFIC COLLECTION
                # Using the robust insert_vectors from milvus_handler
                success = insert_vectors(chunks, vectors, metas, source_name)
                
                if success:
                    total_chunks += len(chunks)
                    print(f"  ✅ Stored {len(vectors)} chunks.")
                else:
                    print(f"      ❌ DB Insert Failed for {source_name}")

        except Exception as e:
            # --- CRITICAL: Print the error so we can see it in terminal ---
            print(f"❌ ERROR processing doc {i}: {e}")
            traceback.print_exc()
            # Continue to next doc instead of crashing the whole server
            continue
            
    return total_chunks

# ==========================================
# 3. UNSTRUCTURED API LOADER (Hybrid Logic)
# ==========================================
def get_extension(file_path: str) -> str:
    return file_path.split(".")[-1].lower()

def load_unstructured_data(file_path):
    print(f"☁️ Sending to Unstructured API: {file_path}")
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    api_url = os.getenv("UNSTRUCTURED_API_URL")
    
    if not api_key:
        print("❌ Error: UNSTRUCTURED_API_KEY missing.")
        return [], None

    try:
        from unstructured.partition.api import partition_via_api
        elements = partition_via_api(
            filename=file_path,
            api_key=api_key,
            api_url=api_url,
            strategy="hi_res",
            infer_table_structure=True,
            extract_image_block_types=["Image", "Table"],
        )
        
        saved_images_count = 0
        for el in elements:
            if el.category in ["Image", "Table"]:
                image_base64 = getattr(el.metadata, "image_base64", None)
                if image_base64:
                    image_filename = f"img_{uuid.uuid4().hex[:8]}.jpg"
                    image_save_path = os.path.join(IMAGE_OUTPUT_DIR, image_filename)
                    with open(image_save_path, "wb") as img_file:
                        img_file.write(base64.b64decode(image_base64))
                    el.metadata.image_path = image_save_path
                    saved_images_count += 1

        print(f"✅ API Success: Retrieved {len(elements)} raw elements & {saved_images_count} images.")
        return elements, IMAGE_OUTPUT_DIR

    except Exception as e:
        print(f"❌ UNSTRUCTURED API ERROR: {e}")
        return [], None

def process_complex_file(file_path):
    print(f"📂 Processing Complex File: {file_path}")
    ext = get_extension(file_path)
    docs = []

    if ext in ["pdf", "docx", "pptx", "png", "jpg", "jpeg", "webp", "xlsx", "html"]:
        elements, _ = load_unstructured_data(file_path)
        if not elements: return []

        current_text_chunk = ""
        for el in elements:
            if el.category in ["Image", "Table"]:
                if current_text_chunk.strip():
                    docs.append(Document(
                        page_content=current_text_chunk.strip(), 
                        metadata={"source": os.path.basename(file_path), "type": "text_block", "title": os.path.basename(file_path)}
                    ))
                    current_text_chunk = "" 
                
                docs.append(Document(
                    page_content=f"[VISION CONTENT: {el.category}]",
                    metadata={
                        "source": os.path.basename(file_path),
                        "type": el.category.lower(),
                        "image_path": getattr(el.metadata, "image_path", ""),
                        "title": f"{el.category} from {os.path.basename(file_path)}"
                    }
                ))

            elif el.category in ["Title", "NarrativeText", "UncategorizedText", "ListItem"]:
                text_content = str(el)
                if el.category == "Title" and len(current_text_chunk) > 500:
                     docs.append(Document(
                        page_content=current_text_chunk.strip(), 
                        metadata={"source": os.path.basename(file_path), "type": "text_block", "title": os.path.basename(file_path)}
                    ))
                     current_text_chunk = f"{text_content}\n"
                else:
                    current_text_chunk += f"{text_content}\n"
                
                if len(current_text_chunk) > 1000:
                    docs.append(Document(
                        page_content=current_text_chunk.strip(), 
                        metadata={"source": os.path.basename(file_path), "type": "text_block", "title": os.path.basename(file_path)}
                    ))
                    current_text_chunk = ""

        if current_text_chunk.strip():
             docs.append(Document(
                page_content=current_text_chunk.strip(), 
                metadata={"source": os.path.basename(file_path), "type": "text_block", "title": os.path.basename(file_path)}
            ))
        
        print(f"📊 Final Count: {len(docs)} Documents (Text + Images) ready for RAG.")
        return docs

    # Simple Text fallback
    try:
        if ext == "txt": return TextLoader(file_path).load()
        if ext == "csv": return CSVLoader(file_path).load()
        if ext == "md": return UnstructuredMarkdownLoader(file_path).load()
        if ext in ["py", "js", "c", "cpp", "java"]: return TextLoader(file_path).load()
    except Exception as e:
        print(f"⚠️ Structured Load Warning: {e}")

    return []

# ==========================================
# 4. HANDLERS
# ==========================================
def process_direct_url(url: str):
    doc = None
    if "youtube.com" in url or "youtu.be" in url: 
        # (Add load_youtube logic if needed, kept brief for stability)
        doc = load_youtube(url)
        pass 
    elif url.startswith("http"): 
        try:
            doc = WebBaseLoader(url).load()[0]
            doc.metadata['source'] = url
            doc.metadata['title'] = url
        except: pass
    if doc: return run_ingestion_pipeline([doc])
    return 0

def process_topic_search_api(topic: str):
    try:
        if not search_tool: return 0
        results = search_tool.invoke({"query": topic})
        if isinstance(results, dict) and 'results' in results: results = results['results']
        urls = [r["url"] for r in results if "url" in r][:5]
        if not urls: return 0
        loader = WebBaseLoader(urls)
        return run_ingestion_pipeline(loader.load())
    except: return 0

async def process_uploaded_file_api(file):
    file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        docs = []
        if file.filename.endswith((".mp3", ".wav")):
            doc = load_audio(file_path)
            if doc: docs = [doc]
        else:
            docs = process_complex_file(file_path)
        return run_ingestion_pipeline(docs)
    finally:
        if os.path.exists(file_path): os.remove(file_path)