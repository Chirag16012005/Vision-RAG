from app.services.milvus import search_similar


def retrieve(query_embedding, k=5):
    """Retrieve similar documents based on query embedding."""
    return search_similar(query_embedding, top_k=k)
