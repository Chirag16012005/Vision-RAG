from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel

from backend.models import (
    IngestResponse,
    UrlIngestRequest,
    TopicIngestRequest,
    ConversationDocumentModel,
)

from backend.services.ingestion import (
    process_uploaded_file_api, 
    process_direct_url, 
    process_topic_search_api,
    search_tool
)
# --- IMPORT CORRECT FUNCTIONS FROM YOUR CONVERSATIONS.PY ---
from backend.db.conversations import (
    add_document,
    get_conversation,
    get_documents_for_conversation,
)
from backend.db.milvus_handler import sanitize_collection_name 

router = APIRouter()

# --- Schemas ---
class TopicSearchRequest(BaseModel):
    topic: str
    seen_urls: Optional[List[str]] = None

# --- Search (No Ingestion) ---
@router.post("/search/query")
async def search_topic_only(request: TopicSearchRequest):
    """
    1. Searches the web.
    2. Returns a list of URLs/Titles.
    3. DOES NOT save to database.
    4. DOES NOT require conversation_id.
    """
    try:
        results = search_tool.invoke({"query": request.topic})
        
        # Normalize results
        raw_results = results.get("results", []) if isinstance(results, dict) else results
        
        # Filter seen URLs
        seen_set = set(request.seen_urls) if request.seen_urls else set()
        new_results = [res for res in raw_results if res.get("url") not in seen_set]
        
        return {
            "results": new_results[:5],
            "total_available": len(new_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document", response_model=ConversationDocumentModel)
async def ingest_document(
    file: UploadFile = File(...), 
    conversation_id: str = Form(...) 
):
    try:
        if not get_conversation(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")

        _ = await process_uploaded_file_api(file)

        namespace = sanitize_collection_name(file.filename)
        
        add_document(
            conversation_id=conversation_id,
            document_name=file.filename,
            document_type=file.content_type or "file",
            vector_namespace=namespace  # <--- CRITICAL: Passing namespace
        )

        # Persisted metadata is stored as a single aggregated record per conversation.
        documents = get_documents_for_conversation(conversation_id)
        if not documents:
            raise HTTPException(status_code=500, detail="Document metadata not recorded")

        document_entry = documents[0]
        mongo_id = document_entry.pop("_id", None)
        document_entry.setdefault("id", str(mongo_id) if mongo_id else conversation_id)
        document_entry.setdefault("document_names", [])
        document_entry.setdefault("document_types", [])
        document_entry.setdefault("vector_namespaces", [])
        document_entry.setdefault("created_at", None)

        return ConversationDocumentModel(**document_entry)
    except HTTPException as exc:
        raise exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url", response_model=IngestResponse)
async def ingest_url(
    request: UrlIngestRequest, 
    conversation_id: str = Query(...)
):
    try:
        count = process_direct_url(request.url)
        namespace = sanitize_collection_name(request.url)
        
        add_document(
            conversation_id=conversation_id,
            document_name=request.url,
            document_type="url",
            vector_namespace=namespace
        )

        return IngestResponse(
            message=f"Successfully processed URL: {request.url}",
            chunks_count=count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

