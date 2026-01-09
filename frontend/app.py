import os
import requests
import streamlit as st
from typing import Dict, Optional, List
from datetime import datetime

# Default Backend URL
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8007")

st.set_page_config(
    page_title="RAG Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================
# SESSION STATE
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "selected_documents" not in st.session_state:
    st.session_state.selected_documents = set()
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = []
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL

# New state for the 2-step topic search
if "topic_search_results" not in st.session_state:
    st.session_state.topic_search_results = []  # Stores the list of articles found
if "last_search_topic" not in st.session_state:
    st.session_state.last_search_topic = ""

# =============================
# STYLES
# =============================
st.markdown(
    """
    <style>
        /* Global Reset & Font */
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui; }
        
        /* Main Background */
        body { background: radial-gradient(circle at top left, #e0faff 0, #e0f2fe 35%, #f9fafb 100%); }
        [data-testid="stAppViewContainer"] { background: transparent; }
        
        /* --- HEADER FIX: Remove the white bar --- */
        header[data-testid="stHeader"] {
            background: transparent; 
        }
        
        /* Adjust main container padding */
        [data-testid="stMainBlockContainer"] { padding: 2rem 2rem 2rem 2rem; }
        
        /* Panel Styling */
        .panel {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 1.25rem;
            padding: 1.25rem;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.35);
        }
        
        /* Button Styling */
        .stButton>button {
            border-radius: 8px;
            background: #0ea5e9;
            color: white;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# BACKEND HELPER
# =============================
def call_backend(endpoint: str, files=None, json=None, params=None):
    url = f"{st.session_state.backend_url.rstrip('/')}{endpoint}"
    try:
        if files:
            response = requests.post(url, files=files, params=params, timeout=300)
        elif json:
            response = requests.post(url, json=json, params=params, timeout=300)
        else:
            response = requests.post(url, params=params, timeout=300)
            
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None

# =============================
# LAYOUT
# =============================
left_col, center_col, right_col = st.columns([1, 2, 1], gap="small")

# --- LEFT: CHATS ---
with left_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 💬 Chats")
    st.divider()

    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.messages:
            # Save current
            first_msg = st.session_state.messages[0].get("content", "") if st.session_state.messages else "New Chat"
            st.session_state.chat_sessions.insert(0, {
                "title": first_msg[:30] + "...",
                "messages": list(st.session_state.messages),
                "created_at": datetime.utcnow().isoformat()
            })
        st.session_state.messages = []
        st.session_state.current_session = None
        st.rerun()

    if st.session_state.chat_sessions:
        st.markdown("#### Recent")
        for idx, session in enumerate(st.session_state.chat_sessions):
            c1, c2 = st.columns([4, 1])
            if c1.button(session["title"], key=f"chat_{idx}", use_container_width=True):
                st.session_state.messages = list(session["messages"])
                st.session_state.current_session = idx
                st.rerun()
            if c2.button("✕", key=f"del_{idx}"):
                st.session_state.chat_sessions.pop(idx)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- CENTER: INGESTION & CHAT ---
with center_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 🧠 Knowledge Base & Chat")
    
    # TABS FOR INGESTION
    tab1, tab2, tab3 = st.tabs(["📄 Upload File", "🔗 Add URL", "🌍 Topic Search"])
    
    # 1. File Upload
    with tab1:
        uploaded_files = st.file_uploader("Upload PDF, TXT, Audio", accept_multiple_files=True)
        if st.button("Process Files", key="btn_file"):
            if uploaded_files:
                with st.spinner("Processing files..."):
                    for up_file in uploaded_files:
                        files = {"file": (up_file.name, up_file.getbuffer(), up_file.type)}
                        resp = call_backend("/ingest/document", files=files)
                        if resp and up_file.name not in st.session_state.documents:
                            st.session_state.documents.append(up_file.name)
                            st.session_state.selected_documents.add(up_file.name)
                    st.success("Files Ingested!")
                    st.rerun()

    # 2. URL Ingestion
    with tab2:
        url_input = st.text_input("Enter YouTube or Website URL")
        if st.button("Process URL", key="btn_url"):
            if url_input:
                with st.spinner(f"Scraping {url_input}..."):
                    resp = call_backend("/ingest/url", json={"url": url_input})
                    if resp:
                        doc_name = f"URL: {url_input[:30]}..."
                        if doc_name not in st.session_state.documents:
                            st.session_state.documents.append(doc_name)
                            st.session_state.selected_documents.add(doc_name)
                        st.success(f"URL Processed! ({resp.get('chunks_count')} chunks)")
                        st.rerun()

    # 3. Topic Search (Review Mode)
    with tab3:
        # If we DON'T have results yet, show the search bar
        if not st.session_state.topic_search_results:
            topic_input = st.text_input("Enter a topic (e.g., 'Latest AI News')", key="topic_search_input")
            
            if st.button("Search Topic", key="btn_search_topic"):
                if topic_input:
                    st.session_state.last_search_topic = topic_input
                    with st.spinner(f"Searching for articles about '{topic_input}'..."):
                        # STEP 1: Call Backend to just SEARCH (not ingest yet)
                        # Ensure your backend has an endpoint /search/query or similar
                        resp = call_backend("/search/query", json={"topic": topic_input})
                        
                        if resp and "results" in resp:
                            st.session_state.topic_search_results = resp["results"]
                            st.rerun()
                        else:
                            st.warning("No results found or Backend does not support search-only.")
        
        # If we DO have results, show the Review List
        else:
            st.info(f"Results for: **{st.session_state.last_search_topic}**")
            
            with st.form("review_form"):
                st.write("Select documents to add to context:")
                
                # Dynamic Checkboxes
                selected_urls = []
                for item in st.session_state.topic_search_results:
                    # item should be {'url': '...', 'title': '...', 'content': '...'}
                    label = f"**{item.get('title', 'Unknown')}** - {item.get('url', '')}"
                    if st.checkbox(label, value=True): # Default Checked
                        selected_urls.append(item.get('url'))
                
                col1, col2 = st.columns(2)
                
                # Button 1: Ingest Selected
                submitted = col1.form_submit_button("✅ Ingest Selected")
                
                # Button 2: Reject / Search Again
                retry = col2.form_submit_button("🔄 Reject / Search Again")
            
            if submitted:
                if not selected_urls:
                    st.warning("You deselected everything! Searching again...")
                    st.session_state.topic_search_results = [] # Clear results to trigger search view
                    st.rerun()
                else:
                    # STEP 2: Ingest the accepted URLs
                    progress_text = st.empty()
                    progress_text.write("⏳ Ingesting selected documents...")
                    
                    count = 0
                    for url in selected_urls:
                        # Use existing URL ingest endpoint
                        resp = call_backend("/ingest/url", json={"url": url})
                        if resp:
                            doc_name = f"WEB: {url[:30]}..."
                            if doc_name not in st.session_state.documents:
                                st.session_state.documents.append(doc_name)
                                st.session_state.selected_documents.add(doc_name)
                            count += 1
                    
                    st.session_state.topic_search_results = [] # Clear results after success
                    st.success(f"Successfully added {count} documents!")
                    st.rerun()

            if retry:
                st.session_state.topic_search_results = [] # Clear results to show search bar again
                st.rerun()

    st.divider()

    # Chat Interface
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Ask about your data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                sel_docs = list(st.session_state.selected_documents)
                resp = call_backend("/qa/ask", params={"question": prompt, "files": ",".join(sel_docs)})
                answer = resp.get("answer", "Error getting answer") if resp else "Backend Error"
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

    st.markdown("</div>", unsafe_allow_html=True)

# --- RIGHT: FILE MANAGER ---
with right_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 📂 Context")
    if st.session_state.documents:
        for doc in st.session_state.documents:
            c1, c2 = st.columns([4, 1])
            is_sel = doc in st.session_state.selected_documents
            if c1.checkbox(doc, value=is_sel, key=f"sel_{doc}"):
                st.session_state.selected_documents.add(doc)
            else:
                st.session_state.selected_documents.discard(doc)
    else:
        st.info("No documents yet.")
    st.markdown("</div>", unsafe_allow_html=True)