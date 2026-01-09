import os
import requests
import streamlit as st
from typing import Dict, Optional
from datetime import datetime

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

if "timeout" not in st.session_state:
    st.session_state.timeout = 20

# =============================
# STYLES (UNCHANGED)
# =============================
st.markdown(
    """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui; }
        body { background: radial-gradient(circle at top left, #e0faff 0, #e0f2fe 35%, #f9fafb 100%); }
        [data-testid="stAppViewContainer"] { background: transparent; }
        [data-testid="stMainBlockContainer"] { padding: 1.5rem 2rem 2rem 2rem; }

        .panel {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 1.25rem;
            padding: 1.25rem;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.35);
        }

        .panel-left { border-top-right-radius: 0.75rem; border-bottom-right-radius: 0.75rem; }
        .panel-center { border-radius: 1.5rem; }
        .panel-right { border-top-left-radius: 0.75rem; border-bottom-left-radius: 0.75rem; }

        .stButton>button {
            border-radius: 999px;
            background: rgba(14, 165, 233, 1);
            color: white;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# BACKEND CALL
# =============================
def call_backend(
    endpoint: str,
    *,
    files: Optional[Dict[str, tuple]] = None,
    params: Optional[Dict[str, str]] = None,
) -> Optional[Dict]:
    url = f"{st.session_state.backend_url.rstrip('/')}{endpoint}"
    try:
        response = requests.post(url, files=files, params=params, timeout=st.session_state.timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None

# =============================
# LAYOUT
# =============================
left_col, center_col, right_col = st.columns([1, 2, 1], gap="small")

# =============================
# LEFT - CHATS
# =============================
with left_col:
    st.markdown('<div class="panel panel-left">', unsafe_allow_html=True)
    st.markdown("### 💬 Chats")
    st.divider()

    if st.button(" New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_session = None
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =============================
# CENTER - UPLOAD + CHAT
# =============================
with center_col:
    st.markdown('<div class="panel panel-center">', unsafe_allow_html=True)
    st.markdown("### 📚 AI Documentation Assistant")
    st.markdown("Upload documents and ask follow-up questions. Answers are grounded in your data.")
    st.divider()

    # ---------- UPLOAD ----------
    st.markdown("#### 📄 Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload files",
        type=["pdf", "png", "jpg", "jpeg", "txt","html","docx","py","md","csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Ingest Documents", use_container_width=True):
        if not uploaded_files:
            st.warning("Please select at least one document.")
        else:
            with st.spinner("Ingesting documents..."):
                for uploaded in uploaded_files:
                    files = {
                        "file": (
                            uploaded.name,
                            uploaded.getbuffer(),
                            uploaded.type or "application/octet-stream",
                        )
                    }
                    payload = call_backend("/ingest/document", files=files)
                    if payload and uploaded.name not in st.session_state.documents:
                        st.session_state.documents.append(uploaded.name)
                        st.session_state.selected_documents.add(uploaded.name)

                st.success("✅ Documents ingested successfully")
                st.rerun()

    st.divider()

    # ---------- CHAT ----------
    st.markdown("#### 💭 Conversation")
    chat_container = st.container(height=400)

    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask a question about selected documents...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        selected_files = list(st.session_state.selected_documents)

        with st.spinner("Thinking..."):
            payload = call_backend(
                "/qa/ask",
                params={
                    "question": prompt,
                    "files": ",".join(selected_files) if selected_files else "",
                },
            )

            answer = payload.get("answer", "No answer returned.") if payload else "Error"
            st.session_state.messages.append({"role": "assistant", "content": answer})

        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =============================
# RIGHT - FILE SELECTION
# =============================
with right_col:
    st.markdown('<div class="panel panel-right">', unsafe_allow_html=True)
    st.markdown("### 📁 Files")
    st.markdown("Select documents to include in the context for Q&A.")
    st.divider()

    if st.session_state.documents:
        st.markdown(f"**{len(st.session_state.documents)} documents**")

        for doc in st.session_state.documents:
            col1, col2 = st.columns([4, 1])

            with col1:
                checked = st.checkbox(
                    doc,
                    key=f"select_{doc}",
                    value=(doc in st.session_state.selected_documents),
                )
                if checked:
                    st.session_state.selected_documents.add(doc)
                else:
                    st.session_state.selected_documents.discard(doc)

            with col2:
                if st.button("✕", key=f"remove_{doc}"):
                    st.session_state.documents.remove(doc)
                    st.session_state.selected_documents.discard(doc)
                    st.rerun()
    else:
        st.caption("No documents uploaded yet")

    st.divider()
    st.markdown("**Storage**")
    st.caption(f"Documents: {len(st.session_state.documents)}")

    st.markdown("</div>", unsafe_allow_html=True)
