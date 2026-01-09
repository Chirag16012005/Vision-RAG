from fastapi import APIRouter, UploadFile
from app.services.chunking import hybrid_chunking
from app.services.embeddings import embeddings
from app.services.vectorstore import store_chunks
from app.services.ocr import extract_text_from_image, extract_text_from_pdf

router = APIRouter()

@router.post("/document")
async def ingest_document(file: UploadFile):
    file_bytes = await file.read()
    filename = file.filename.lower()

    if filename.endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(file_bytes)

    elif filename.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)

    else:
        text = file_bytes.decode("utf-8")

    chunks = hybrid_chunking(text)
    chunk_embeddings = embeddings.embed_documents(chunks)
    store_chunks(chunks, chunk_embeddings)

    return {
        "filename": file.filename,
        "chunks_created": len(chunks)
    }
@router.post("/documents")
async def ingest_documents(files: list[UploadFile]):
    #functionality to be implemented
    return {"message": "Bulk document ingestion not yet implemented."}