import re
import os
import hashlib
from typing import Any, Dict, List

import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from pymilvus import (
    connections,
    Collection,
    utility,
    FieldSchema, 
    CollectionSchema, 
    DataType
)

load_dotenv()

# --- CONNECT TO MILVUS ---
def connect_to_milvus():
    try:
        connections.connect(alias="default", host="localhost", port="19530")
        return True
    except Exception as e:
        print(f"⚠️ Milvus Connection Error: {e}")
        return False

# ALIAS: This makes 'connect_db' work in main.py
connect_db = connect_to_milvus 

def sanitize_collection_name(filename: str) -> str:
    """
    Converts filename to valid Milvus collection name.
    """
    if not filename: return "col_unknown"
    
    # 1. Replace non-alphanumeric chars with underscore
    clean = re.sub(r'[^a-zA-Z0-9]', '_', filename)
    
    # 2. Safety Truncation (Keep it under 100 chars)
    if len(clean) > 80:
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
        clean = clean[:80] + "_" + hash_suffix
        
    # 3. Prefix with 'col_' to ensure it starts with a letter
    return f"col_{clean}"

def create_collection(collection_name: str, drop_if_exists=False):
    """
    Creates the collection with the CORRECT schema.
    """
    try:
        # Check existence safely
        exists = utility.has_collection(collection_name)
        
        if drop_if_exists and exists:
            print(f"♻️ Dropping old collection: {collection_name}")
            utility.drop_collection(collection_name)
            exists = False

        if exists:
            return Collection(collection_name)
        
        print(f"🆕 Creating new collection bucket: {collection_name}")
        
        # --- SCHEMA DEFINITION ---
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="image_path", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1000),
        ]
        
        schema = CollectionSchema(fields, description=f"Collection for {collection_name}")
        collection = Collection(name=collection_name, schema=schema)
        
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="vector", index_params=index_params)
        return collection

    except Exception as e:
        print(f"❌ MILVUS COLLECTION ERROR: {e}")
        raise e

def insert_vectors(chunks, embeddings, metas, filename):
    """
    Inserts data into the SPECIFIC collection.
    """
    if not chunks:
        return False
    
    connect_to_milvus()
    col_name = sanitize_collection_name(filename)
    
    # 1. Try to get existing collection
    try:
        collection = create_collection(col_name, drop_if_exists=False)
    except Exception:
        return False
    
    # 2. Prepare Data
    data = [
        embeddings,                                  # vector
        chunks,                                      # text
        [m.get('source', '') for m in metas],        # source
        [m.get('type', 'text') for m in metas],      # type
        [m.get('image_path', '') for m in metas],    # image_path
        [m.get('title', '') for m in metas]          # title
    ]
    
    # 3. Try to Insert
    try:
        collection.insert(data)
        collection.flush()
        print(f"✅ Inserted {len(chunks)} chunks into collection: {col_name}")
        return True
    except Exception as e:
        print(f"⚠️ Insert failed, retrying with schema fix: {e}")
        try:
            # 4. If failed, DROP and RECREATE
            collection = create_collection(col_name, drop_if_exists=True)
            collection.insert(data)
            collection.flush()
            print(f"✅ RECOVERY SUCCESS: Inserted {len(chunks)} chunks.")
            return True
        except Exception as e2:
            print(f"❌ CRITICAL: Failed to recover {col_name}: {e2}")
            return False

# --- MISSING FUNCTION ADDED HERE ---
def list_document_collections():
    """Returns a list of all collections currently in Milvus."""
    connect_to_milvus()
    return utility.list_collections()

def search_multiple_collections(query_vector: List[float], file_names: List[str], top_k_per_col: int = 5) -> List[Dict[str, Any]]:
    """
    Iterates through user-selected files and searches their specific collections.
    """
    connect_to_milvus()
    all_candidates = []

    for filename in file_names:
        candidate_name = filename
        if not utility.has_collection(candidate_name):
            candidate_name = sanitize_collection_name(filename)

        if not utility.has_collection(candidate_name):
            print(f"⚠️ Collection not found for: {filename} (checked {candidate_name})")
            continue

        collection = Collection(candidate_name)
        collection.load()

        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        # Search this specific bucket
        results = collection.search(
            data=[query_vector],
            anns_field="vector", 
            param=search_params,
            limit=top_k_per_col,
            # We explicitly fetch the vector to perform MMR math later
            output_fields=["text", "source", "type", "image_path", "title", "vector"] 
        )

        # Flatten results
        for hits in results:
            for hit in hits:
                all_candidates.append({
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.entity.get("text"),
                    "source": hit.entity.get("source"),
                    "type": hit.entity.get("type"),
                    "image_path": hit.entity.get("image_path"),
                    "title": hit.entity.get("title"),
                    "embedding": hit.entity.get("vector") # Critical for MMR
                })

    return all_candidates

def mmr_sort(query_embedding: List[float], docs: List[Dict[str, Any]], k: int = 5, lambda_mult: float = 0.5) -> List[Dict[str, Any]]:
    """
    Selects diverse results from the aggregated candidates list.
    """
    if not docs: return []
    
    # Extract vectors
    doc_embeddings = [d['embedding'] for d in docs]
    
    # 1. Best Match
    sims_to_query = cosine_similarity([query_embedding], doc_embeddings)[0]
    best_idx = np.argmax(sims_to_query)
    
    selected_indices = [best_idx]
    candidate_indices = [i for i in range(len(docs)) if i != best_idx]

    # 2. Iteratively Select Rest
    while len(selected_indices) < min(k, len(docs)):
        best_mmr_score = -np.inf
        idx_to_add = -1

        for idx in candidate_indices:
            relevance = sims_to_query[idx]
            
            # Diversity Check
            current_vec = [doc_embeddings[idx]]
            selected_vecs = [doc_embeddings[i] for i in selected_indices]
            redundancy = np.max(cosine_similarity(current_vec, selected_vecs)[0])
            
            mmr_score = (lambda_mult * relevance) - ((1 - lambda_mult) * redundancy)
            
            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                idx_to_add = idx

        if idx_to_add != -1:
            selected_indices.append(idx_to_add)
            candidate_indices.remove(idx_to_add)
        else:
            break

    return [docs[i] for i in selected_indices]

def retrieve_documents(user_query: str, selected_files: List[str], k: int = 5) -> List[Dict[str, Any]]:
    """
    Main retrieval function called by QA Router.
    """
    print(f"🔍 Retrieving for: '{user_query}' across {len(selected_files)} files")

    if not selected_files:
        return []

    # 1. Embed Query
    from backend.services.ingestion import embed_query  # Lazy import avoids circular dependency

    query_vec = embed_query(user_query)

    # 2. Search Specific Buckets (Get 3x candidates per file)
    candidates = search_multiple_collections(query_vec, selected_files, top_k_per_col=k*3)

    if not candidates:
        return []

    # 3. Apply MMR Filter
    final_docs = mmr_sort(query_vec, candidates, k=k)

    # 4. Clean Output (Drop vectors to save bandwidth)
    for doc in final_docs:
        doc.pop("embedding", None)
        
    return final_docs


def delete_vector_namespaces(namespaces: List[str]) -> None:
    """Drop Milvus collections associated with the provided namespaces."""
    if not namespaces:
        return

    if not connect_to_milvus():
        print("⚠️ Unable to connect to Milvus; skipping namespace cleanup.")
        return

    for namespace in namespaces:
        if not namespace:
            continue
        try:
            if utility.has_collection(namespace):
                utility.drop_collection(namespace)
                print(f"🗑️ Dropped Milvus collection: {namespace}")
            else:
                print(f"ℹ️ Milvus collection not found (already removed): {namespace}")
        except Exception as exc:
            print(f"⚠️ Failed to drop Milvus collection '{namespace}': {exc}")