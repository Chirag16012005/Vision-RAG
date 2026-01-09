from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.models import IngestResponse, UrlIngestRequest, TopicIngestRequest
from backend.services.ingestion import (
    process_uploaded_file_api, 
    process_direct_url, 
    process_topic_search_api,
    search_tool  # Imported from ingestion service
)

router = APIRouter()

# --- New Model for Search with Exclusion ---
class TopicSearchRequest(BaseModel):
    topic: str
    seen_urls: Optional[List[str]] = []

@router.post("/search/query")
async def search_topic_only(request: TopicSearchRequest):
    """
    Searches the web and returns URLs/Titles.
    Filters out 'seen_urls' to ensure fresh results on retry.
    """
    try:
        # 1. Invoke Search (Fetches top 20)
        results = search_tool.invoke({"query": request.topic})
        
        # 2. Normalize results
        raw_results = []
        if isinstance(results, list):
            raw_results = results
        elif isinstance(results, dict) and "results" in results:
            raw_results = results["results"]
            
        # 3. Filter out seen URLs
        seen_set = set(request.seen_urls) if request.seen_urls else set()
        
        new_results = [
            res for res in raw_results 
            if res.get("url") not in seen_set
        ]
        
        # 4. Return top 5 fresh results
        return {
            "results": new_results[:5],
            "total_available": len(new_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Existing Endpoints ---

@router.post("/document", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Uploads and ingests a file (PDF, TXT, Audio)."""
    try:
        count = await process_uploaded_file_api(file)
        return IngestResponse(
            message=f"Successfully processed {file.filename}",
            chunks_count=count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/url", response_model=IngestResponse)
async def ingest_url(request: UrlIngestRequest):
    """Ingests a direct URL (YouTube, Wiki, Website)."""
    try:
        count = process_direct_url(request.url)
        return IngestResponse(
            message=f"Successfully processed URL: {request.url}",
            chunks_count=count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topic", response_model=IngestResponse)
async def ingest_topic(request: TopicIngestRequest):
    """(Legacy) Direct topic ingestion."""
    try:
        count = process_topic_search_api(request.topic)
        return IngestResponse(
            message=f"Successfully searched and ingested topic: {request.topic}",
            chunks_count=count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))