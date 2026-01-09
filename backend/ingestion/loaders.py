from pathlib import Path
from typing import List

from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredImageLoader,
)


def load_document(file_path: str) -> List[Document]:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)

    elif ext in [".doc", ".docx"]:
        loader = Docx2txtLoader(file_path)

    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")

    elif ext in [".jpg", ".jpeg", ".png"]:
        loader = UnstructuredImageLoader(file_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return loader.load()
