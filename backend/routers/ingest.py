from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models import IngestResponse, UrlIngestRequest, TopicIngestRequest
from backend.services.ingestion import process_uploaded_file_api, process_direct_url, process_topic_search_api

router = APIRouter()

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
    """Searches the web for a topic and ingests top results."""
    try:
        count = process_topic_search_api(request.topic)
        return IngestResponse(
            message=f"Successfully searched and ingested topic: {request.topic}",
            chunks_count=count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))