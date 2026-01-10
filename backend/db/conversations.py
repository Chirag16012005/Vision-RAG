from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from backend.db.mongo import (
    ensure_connection,
    conversations_col,
    messages_col,
    summaries_col,
    conversation_documents_col,
    feedbacks_col
)
from backend.db.milvus_handler import delete_vector_namespaces


def _require_connection() -> None:
    if not ensure_connection():
        raise RuntimeError("MongoDB connection is not available")


def add_document(
    conversation_id: str,
    document_name: str,
    document_type: str,
    vector_namespace: str,
) -> Dict[str, Any]:
    """
    Link a document to a conversation.
    This stores document metadata as arrays under a single document identified
    by `conversation_id`. If no record exists yet, it creates one.
    """
    _require_connection()
    now = datetime.utcnow()

    # Try to append to existing conversation_documents doc
    result = conversation_documents_col.find_one_and_update(
        {"conversation_id": conversation_id},
        {
            "$push": {
                "document_names": document_name,
                "document_types": document_type,
                "vector_namespaces": vector_namespace,
            },
            "$setOnInsert": {"created_at": now, "id": str(uuid4())},
        },
        upsert=True,
    )

    # If find_one_and_update didn't return the new doc, fetch it explicitly.
    if not result:
        result = conversation_documents_col.find_one({"conversation_id": conversation_id})

    return result


def get_documents_for_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """
    Returns all documents linked to a conversation.
    Used when reopening a past chat.
    """
    _require_connection()
    doc = conversation_documents_col.find_one({"conversation_id": conversation_id}, {"_id": 0})
    return [doc] if doc else []


def get_document_names_for_conversation(conversation_id: str) -> List[str]:
    """
    Lightweight helper for UI (document picker).
    """
    _require_connection()
    doc = conversation_documents_col.find_one({"conversation_id": conversation_id}, {"_id": 0, "document_names": 1})
    return doc.get("document_names", []) if doc else []


def get_vector_namespaces(
    conversation_id: str,
    document_names: List[str],
) -> List[str]:
    """
    Used by retriever to scope vector search.
    """
    _require_connection()
    doc = conversation_documents_col.find_one({"conversation_id": conversation_id}, {"_id": 0, "document_names": 1, "vector_namespaces": 1})
    if not doc:
        return []

    name_to_namespace = {n: ns for n, ns in zip(doc.get("document_names", []), doc.get("vector_namespaces", []))}
    return [name_to_namespace.get(name) for name in document_names if name in name_to_namespace]


def delete_documents_for_conversation(conversation_id: str) -> bool:
    """
    Cleanup when a conversation is deleted.
    """
    _require_connection()
    conversation_documents_col.delete_many({"conversation_id": conversation_id})
    return True


def get_document_names(conversation_id: str) -> List[str]:
    """Compatibility wrapper used by routers: return list of document names."""
    return get_document_names_for_conversation(conversation_id)



def create_conversation(user_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    _require_connection()
    cid = str(uuid4())
    now = datetime.utcnow()
    doc = {
        "id": cid,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }
    conversations_col.insert_one(doc)
    return doc


def update_conversation_title(conversation_id: str, title: str) -> None:
    _require_connection()
    conversations_col.update_one(
        {"id": conversation_id},
        {"$set": {"title": title, "updated_at": datetime.utcnow()}},
    )


def list_conversations():
    _require_connection()
    return list(
        conversations_col.find(
            {},
            {"_id": 0, "id": 1, "title": 1, "updated_at": 1},
        ).sort("updated_at", -1)
    )


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    _require_connection()
    return conversations_col.find_one({"id": conversation_id})


def delete_conversation(conversation_id: str) -> bool:
    _require_connection()
    doc_meta = conversation_documents_col.find_one(
        {"conversation_id": conversation_id},
        {"_id": 0, "vector_namespaces": 1},
    )
    conversations_col.delete_one({"id": conversation_id})
    messages_col.delete_many({"conversation_id": conversation_id})
    summaries_col.delete_one({"conversation_id": conversation_id})
    conversation_documents_col.delete_many({"conversation_id": conversation_id})
    feedbacks_col.delete_many({"conversation_id": conversation_id})
    if doc_meta:
        namespaces = doc_meta.get("vector_namespaces") or []
        delete_vector_namespaces(namespaces)
    return True


def add_message(conversation_id: str, role: str, content: str, token_count: int, rating: Optional[int] = None) -> Dict[str, Any]:
    _require_connection()
    mid = str(uuid4())
    now = datetime.utcnow()
    doc = {
        "id": mid,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "token_count": token_count,
        "rating": rating,
        "created_at": now,
    }
    messages_col.insert_one(doc)
    # update conversation updated_at
    conversations_col.update_one({"id": conversation_id}, {"$set": {"updated_at": now}})
    return doc


def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    _require_connection()
    docs = list(messages_col.find({"conversation_id": conversation_id}).sort([("created_at", 1)]))
    return docs


def get_message(message_id: str) -> Optional[Dict[str, Any]]:
    _require_connection()
    return messages_col.find_one({"id": message_id})


def upsert_summary(conversation_id: str, summary: str, token_count: int) -> Dict[str, Any]:
    _require_connection()
    now = datetime.utcnow()
    doc = {
        "conversation_id": conversation_id,
        "summary": summary,
        "token_count": token_count,
        "updated_at": now,
    }
    summaries_col.update_one({"conversation_id": conversation_id}, {"$set": doc}, upsert=True)
    return doc


def get_summary(conversation_id: str) -> Optional[Dict[str, Any]]:
    _require_connection()
    return summaries_col.find_one({"conversation_id": conversation_id})

def add_feedback(
    message_id: str, user_id: str, conversation_id: str, rating: int
) -> Dict[str, Any]:
    """Store a feedback record tied to a specific AI message.

    Fields: id, message_id, user_id, conversation_id, rating, created_at
    """
    fid = str(uuid4())
    now = datetime.utcnow()
    doc = {
        "id": fid,
        "message_id": message_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "rating": rating,
        "created_at": now,
    }
    _require_connection()
    feedbacks_col.insert_one(doc)
    return doc


def get_feedback_for_conversation(
    user_id: str, conversation_id: str
) -> List[Dict[str, Any]]:
    """Return all feedback records for a given user and conversation.

    This is used by the feedback-driven instruction builder.
    """
    _require_connection()
    return list(
        feedbacks_col.find(
            {"user_id": user_id, "conversation_id": conversation_id}, {"_id": 0}
        )
    )