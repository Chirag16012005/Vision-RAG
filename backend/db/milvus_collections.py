from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)

COLLECTION_NAME = "test_collection"
VECTOR_DIM = 4

connections.connect(alias="default", host="localhost", port="19530")

if utility.has_collection(COLLECTION_NAME):
    collection = Collection(name=COLLECTION_NAME)
else:
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
    ]
    schema = CollectionSchema(fields=fields, description="test collection")
    collection = Collection(name=COLLECTION_NAME, schema=schema)

if not collection.has_index():
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 128},
    }
    collection.create_index(field_name="embedding", index_params=index_params)

vectors = [[0.1, 0.2, 0.3, 0.4]]

if collection.num_entities == 0:
    collection.insert([vectors])
    collection.flush()

collection.load()

search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=vectors,
    anns_field="embedding",
    param=search_params,
    limit=1,
)

print("Search result:", results)