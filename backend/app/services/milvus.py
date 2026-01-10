import re
import os
import hashlib
from dotenv import load_dotenv
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
try:
    connections.connect(alias="default", host="localhost", port="19530")
    print("✅ Connected to Milvus Database")
except Exception as e:
    print(f"⚠️ Milvus Connection Error: {e}")

def sanitize_collection_name(filename: str) -> str:
    """
    Converts a filename/URL into a valid, safe Milvus collection name.
    1. Removes special chars.
    2. Truncates if too long (Milvus limit is ~255 chars).
    3. Adds hash to ensure uniqueness if truncated.
    """
    # 1. Replace non-alphanumeric chars with underscore
    clean = re.sub(r'[^a-zA-Z0-9]', '_', filename)
    
    # 2. Safety Truncation (Keep it under 100 chars to be safe)
    if len(clean) > 100:
        # Create a unique hash of the FULL original name
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
        # Take first 90 chars + underscore + 8 char hash
        clean = clean[:90] + "_" + hash_suffix
        
    # 3. Prefix with 'col_' to ensure it starts with a letter
    return f"col_{clean}"

def create_collection_if_not_exists(collection_name: str):
    """
    Checks if a specific file's collection exists; if not, creates it.
    """
    # Check if exists
    try:
        if utility.has_collection(collection_name):
            return Collection(collection_name)
    except Exception as e:
        print(f"⚠️ Error checking collection {collection_name}: {e}")
    
    print(f"🆕 Creating new collection bucket: {collection_name}")
    
    # 1. Define Fields
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
    
    # 2. Create Collection
    try:
        collection = Collection(name=collection_name, schema=schema)
        
        # 3. Create Index
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="vector", index_params=index_params)
        return collection
    except Exception as e:
        print(f"❌ Failed to create collection '{collection_name}': {e}")
        # Re-raise so the ingestion pipeline knows it failed
        raise e

def insert_vectors(chunks, embeddings, metas, filename):
    """
    Inserts data into the SPECIFIC collection for the given filename.
    """
    if not chunks:
        return False

    # 1. Determine the collection name
    col_name = sanitize_collection_name(filename)
    
    try:
        collection = create_collection_if_not_exists(col_name)
        
        # 2. Prepare Data
        data = [
            embeddings,                                  # vector
            chunks,                                      # text
            [m.get('source', '') for m in metas],        # source
            [m.get('type', 'text') for m in metas],      # type
            [m.get('image_path', '') for m in metas],    # image_path
            [m.get('title', '') for m in metas]          # title
        ]
        
        # 3. Insert and Flush
        collection.insert(data)
        collection.flush()
        print(f"✅ Inserted {len(chunks)} chunks into collection: {col_name}")
        return True
        
    except Exception as e:
        print(f"❌ Milvus Insert Error for {col_name}: {e}")
        return False