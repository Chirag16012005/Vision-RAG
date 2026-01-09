import re
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.embeddings import embeddings

semantic_chunker = SemanticChunker(
    embeddings=embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95
)

token_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=80
)

def split_by_headings(text):
    return [s.strip() for s in re.split(r"\n#+\s+", text) if s.strip()]

def hybrid_chunking(text):
    chunks = []
    for section in split_by_headings(text):
        try:
            semantic_chunks = semantic_chunker.split_text(section)
        except ValueError:
            semantic_chunks = [section]
        for sc in semantic_chunks:
            chunks.extend(token_splitter.split_text(sc))
    return chunks
