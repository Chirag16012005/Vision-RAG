from fastapi import APIRouter
from app.services.embeddings import embeddings
from app.services.rag import retrieve

router = APIRouter()

@router.post("/ask")
def ask(question: str):
    q_emb = embeddings.embed_query(question)
    contexts = retrieve(q_emb)
    return {"answer": " ".join(contexts)}
