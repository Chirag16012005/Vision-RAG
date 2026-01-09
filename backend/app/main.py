from fastapi import FastAPI
from app.routers import ingest, qa

app = FastAPI()
app.include_router(ingest.router, prefix="/ingest")
app.include_router(qa.router, prefix="/qa")
