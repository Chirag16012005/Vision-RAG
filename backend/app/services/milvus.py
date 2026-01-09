import os
from typing import List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = os.getenv("MILVUS_COLLECTION", "documents")
DEFAULT_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
TEXT_MAX_LENGTH = int(os.getenv("MILVUS_TEXT_MAX_LENGTH", "4096"))
INDEX_TYPE = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
METRIC_TYPE = os.getenv("MILVUS_METRIC_TYPE", "IP")
NLIST = int(os.getenv("MILVUS_NLIST", "1024"))
NPROBE = int(os.getenv("MILVUS_NPROBE", "16"))


def _connect() -> None:
    if connections.has_connection("default"):
        return
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)


def _create_collection(vector_dim: int) -> Collection:
    # Collection stores chunk text and embedding vector.
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=TEXT_MAX_LENGTH),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
    ]
    schema = CollectionSchema(fields=fields, description="RAG document chunks")
    collection = Collection(name=COLLECTION_NAME, schema=schema)
    index_params = {
        "index_type": INDEX_TYPE,
        "metric_type": METRIC_TYPE,
        "params": {"nlist": NLIST},
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    return collection


def _ensure_collection(vector_dim: Optional[int] = None) -> Collection:
    _connect()
    dim = vector_dim or DEFAULT_DIM
    if utility.has_collection(COLLECTION_NAME):
        collection = Collection(name=COLLECTION_NAME)
        embed_field = next(f for f in collection.schema.fields if f.name == "embedding")
        existing_dim = embed_field.params.get("dim")
        if existing_dim != dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {existing_dim}, got {dim}."
            )
        if not collection.has_index():
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": INDEX_TYPE,
                    "metric_type": METRIC_TYPE,
                    "params": {"nlist": NLIST},
                },
            )
        return collection
    return _create_collection(dim)


def store_chunks(chunks: List[str], embeddings: List[List[float]]) -> int:
    if not chunks or not embeddings:
        return 0
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings must have the same length.")
    vector_dim = len(embeddings[0]) if embeddings[0] else DEFAULT_DIM
    collection = _ensure_collection(vector_dim)
    collection.insert([chunks, embeddings])
    collection.flush()
    return len(chunks)


def search_similar(query_embedding: List[float], top_k: int = 5) -> List[str]:
    if not query_embedding:
        return []
    collection = _ensure_collection(len(query_embedding))
    if collection.num_entities == 0:
        return []
    collection.load()
    params = {"metric_type": METRIC_TYPE}
    if INDEX_TYPE.upper().startswith("IVF"):
        params["params"] = {"nprobe": NPROBE}
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=params,
        limit=top_k,
        output_fields=["text"],
    )
    contexts: List[str] = []
    for hits in results:
        for hit in hits:
            text = hit.entity.get("text")
            if text:
                contexts.append(text)
    return contexts
