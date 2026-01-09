from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# Milvus Config
HOST = "127.0.0.1"
PORT = "19530"
COLLECTION_NAME = "RAG_Documents"
DIMENSION = 384  # Matches 'all-MiniLM-L6-v2'

def connect_db():
    connections.connect("default", host=HOST, port=PORT)

def init_collection():
    """Initializes the collection if it doesn't exist."""
    connect_db()
    
    if not utility.has_collection(COLLECTION_NAME):
        print(f"Creating Milvus collection: {COLLECTION_NAME}")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION)
        ]
        schema = CollectionSchema(fields, description="Document Store for RAG")
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="vector", index_params=index_params)
        collection.load()
    else:
        Collection(COLLECTION_NAME).load()

def insert_vectors(chunks: list, vectors: list, source: str):
    """Inserts processed chunks and vectors into Milvus."""
    connect_db()
    collection = Collection(COLLECTION_NAME)
    
    data = [
        chunks,
        [source] * len(chunks),
        vectors
    ]
    collection.insert(data)
    collection.flush()
    print(f"💾 Inserted {len(chunks)} chunks from {source} into Milvus.")

def search_vectors(query_vector, file_filters=None, top_k=5):
    """Searches for similar vectors."""
    connect_db()
    collection = Collection(COLLECTION_NAME)
    
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    
    expr = None
    if file_filters:
        files_str = ",".join([f"'{f}'" for f in file_filters])
        expr = f"source in [{files_str}]"

    results = collection.search(
        data=[query_vector],
        anns_field="vector",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=["text", "source"]
    )
    
    if not results: return []
    return results[0]