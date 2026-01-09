from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.routers import ingest, qa
from backend.db.milvus_handler import init_collection
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up: Initializing Milvus...")
    init_collection()
    yield
    # Shutdown
    print("🛑 Shutting down...")

app = FastAPI(title="RAG Backend API", lifespan=lifespan)

app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(qa.router, prefix="/qa", tags=["Q&A"])

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8007, reload=True)