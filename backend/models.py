from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ConversationModel(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MessageModel(BaseModel):
    id: str
    conversation_id: str
    role: str  # 'human' or 'ai'
    content: str
    token_count: int
    rating: Optional[int] = None
    created_at: Optional[datetime] = None


class ConversationSummaryModel(BaseModel):
    conversation_id: str
    summary: str
    token_count: int
    updated_at: Optional[datetime] = None

class ConversationDocumentModel(BaseModel):
    id: str
    conversation_id: str
    document_names: List[str]
    document_types: List[str]
    vector_namespaces: List[str]
    created_at: Optional[datetime] = None

class HealthCheck(BaseModel):
    status: str = "ok"

# Response Model for Ingestion
class IngestResponse(BaseModel):
    message: str
    chunks_count: int
    status: str

# Request Model for URL Ingestion
class UrlIngestRequest(BaseModel):
    url: str

# Request Model for Topic Search & Ingestion
class TopicIngestRequest(BaseModel):
    topic: str

# Q&A Models
class QARequest(BaseModel):
    question: str
    files: Optional[str] = None 

class QAResponse(BaseModel):
    answer: str
    sources: List[str]