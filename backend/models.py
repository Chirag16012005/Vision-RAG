from pydantic import BaseModel
from typing import List, Optional

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