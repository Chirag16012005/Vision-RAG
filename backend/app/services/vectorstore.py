from app.services.milvus import store_chunks as milvus_store_chunks


def store_chunks(chunks: list, embeddings: list):
    """Store text chunks and their embeddings in Milvus."""
    return milvus_store_chunks(chunks, embeddings)
