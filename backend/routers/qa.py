from fastapi import APIRouter, HTTPException
from typing import Optional
from backend.models import QAResponse
from backend.services.llm_engine import generate_answer

router = APIRouter()

@router.post("/ask", response_model=QAResponse)
async def ask_question(question: str, files: Optional[str] = ""):
    """
    Receives 'question' and comma-separated 'files' via Query Parameters.
    """
    try:
        file_list = [f.strip() for f in files.split(",")] if files else []
        answer, sources = generate_answer(question, file_list)
        return QAResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))