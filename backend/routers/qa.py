from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from backend.db import conversations as conv_db
from backend.db.mongo import conversations_col
from backend.db.conversations import get_document_names

# External dependencies (must exist)
from backend.services.llm_engine import llm
from backend.db.milvus_handler import retrieve_documents


router = APIRouter()

# -------------------- CONSTANTS --------------------
MAX_ALLOWED_CONTEXT = 8000
RESERVED_SUMMARY_TOKENS = 500

# -------------------- MODELS --------------------

class ConversationItem(BaseModel):
    id: str
    title: Optional[str]
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: List[ConversationItem]


class Message(BaseModel):
    id: str
    role: str
    text: str


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[Message]


class DeleteConversationResponse(BaseModel):
    conversation_id: str
    deleted: bool


class ChatRequest(BaseModel):
    user_query: str
    selected_documents: List[str] = Field(default_factory=list)


class NewChatRequest(BaseModel):
    user_id: Optional[str] = None


class ConversationCreateResponse(BaseModel):
    conversation_id: str
    response: Optional[str] = None
    title: Optional[str] = None
    
class DocumentUploadResponse(BaseModel):
    document_id: str
    document_name: str
    conversation_id: str
    status: str


class ConversationDocumentsResponse(BaseModel):
    conversation_id: str
    documents: List[str]


class ChatWithDocsRequest(BaseModel):
    user_query: str
    selected_documents: List[str] = Field(default_factory=list)
    
# -------------------- ⭐ FEEDBACK MODELS (ADDED) --------------------


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    rating: int


class FeedbackResponse(BaseModel):
    message_id: str
    rating: int
    status: str
# -------------------- HELPERS --------------------
def count_tokens(summary, messages):
    tokens = sum(m["token_count"] for m in messages)
    if summary:

        tokens += summary["token_count"]
    return tokens


def total_tokens(summary: Optional[dict], messages: List[dict]) -> int:
    total = 0
    if summary and "token_count" in summary:
        total += summary["token_count"]
    for msg in messages:
        total += msg.get("token_count", 0)
    return total


def estimate_text_tokens(text: str) -> int:
    # Rough heuristic until a tokenizer is wired in
    return max(len(text.split()), 1) if text else 0


def prune_and_summarize(
    conversation_id: str,
    messages: list,
    summary: dict | None,
    llm,
    count_tokens,
):
    active_messages = messages.copy()
    archived_messages = []

    while (
        total_tokens(summary, active_messages)
        + RESERVED_SUMMARY_TOKENS
        > MAX_ALLOWED_CONTEXT
    ):
        if len(active_messages) < 2:
            break

        archived_messages.extend([active_messages.pop(0), active_messages.pop(0)])

    if not archived_messages:
        return active_messages, summary
    

    summary_input = ""
    if summary:
        summary_input += f"Previous summary:\n{summary['summary']}\n\n"

    for m in archived_messages:
        summary_input += f"{m['role']}: {m['content']}\n"

    # Use summary_llm(context, prompt) signature (caller will implement)
    summary_prompt = "Create a concise running summary of this conversation."
    new_summary_text = llm(summary_input, summary_prompt)

    return (
        active_messages,
        conv_db.upsert_summary(
            conversation_id,
            new_summary_text,
            count_tokens(new_summary_text),
        ),
    )


def build_context(conversation_id: str, summary, messages):
    context = ""

    # ⭐ FEEDBACK INJECTION (ADDED)
    feedback_instruction = get_feedback_instruction_for_conversation(conversation_id)
    if feedback_instruction:
        context += f"System instruction:\n{feedback_instruction}\n\n"

    if summary:
        context += f"Conversation summary:\n{summary['summary']}\n\n"

    for m in messages:
        context += f"{m['role'].capitalize()}: {m['content']}\n"

    return context


def process_user_query(
    conversation_id: str,
    user_query: str,
    selected_documents: List[str],
) -> str:
    conversation = conv_db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # --------------------------------------------------
    # 🔥 AUTO-GENERATE TITLE (ONLY IF NONE)
    # --------------------------------------------------
    if conversation.get("title") is None:
        title = generate_conversation_title(user_query)
        conv_db.update_conversation_title(conversation_id, title)

    # --------------------------------------------------
    # Load history + summary
    # --------------------------------------------------
    messages = conv_db.get_conversation_history(conversation_id)
    summary = conv_db.get_summary(conversation_id)

    context_messages, new_summary = prune_and_summarize(
        conversation_id,
        messages,
        summary,
        llm,
        count_tokens,
    )

    context = build_context(conversation_id, new_summary, context_messages)

    # --------------------------------------------------
    # 🔥 Document selection enforced
    # --------------------------------------------------
    if not selected_documents:
        raise HTTPException(
            status_code=400,
            detail="No document selected for this query",
        )

    # --------------------
    # Query rewriting for better retrieval
    # --------------------
    rewrite_prompt = (
        "Rewrite the user's query to a concise retrieval query. "
        "Preserve important entities and keywords, remove chit-chat, and return only the rewritten query."
    )
    try:
        rewritten_query = llm(user_query, rewrite_prompt)
        if not rewritten_query or not isinstance(rewritten_query, str):
            rewritten_query = user_query
    except Exception:
        rewritten_query = user_query

    retrieved_docs = retrieve_documents(
        rewritten_query,
        selected_documents,
    )

    context += f"\n\nRelevant documents:\n{retrieved_docs}"
    context += f"\n\nHuman: {user_query}\nAI:"

    # Use llm(context, prompt) signature (caller will implement)
    response_prompt = "Answer the user based on the provided context."
    ai_response = llm(context, response_prompt)

    conv_db.add_message(
        conversation_id,
        "human",
        user_query,
        estimate_text_tokens(user_query),
    )

    conv_db.add_message(
        conversation_id,
        "ai",
        ai_response,
        estimate_text_tokens(ai_response),
    )

    return ai_response


def generate_conversation_title(user_query: str) -> str:
    title_prompt = "Generate a short (max 6 words) title for the given user query."
    return llm(user_query, title_prompt).strip().replace('"', '')
    
# -------------------- ⭐ FEEDBACK LOGIC (CONVERSATION-SCOPED) --------------------


def get_feedback_instruction_for_conversation(conversation_id: str) -> Optional[str]:
    """
    Builds feedback instruction using feedback from the SAME conversation.
    """
    conversation = conv_db.get_conversation(conversation_id)
    if not conversation:
        return None

    user_id = conversation.get("user_id")
    if not user_id:
        return None

    feedbacks = conv_db.get_feedback_for_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if not feedbacks:
        return None

    ratings = [f["rating"] for f in feedbacks]
    avg_rating = sum(ratings) / len(ratings)

    if avg_rating <= 2:
        return (
            "User is dissatisfied in this conversation. "
            "Be very clear, detailed, step-by-step, and avoid vague explanations."
        )
    elif avg_rating <= 3:
        return "User wants clearer explanations with examples in this conversation."
    else:
        return (
            "User is satisfied with answers in this conversation. "
            "Maintain current clarity and depth."
        )

        
def validate_feedback_rating(rating: int):
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5",
        )


# -------------------- ROUTES --------------------

@router.get("/conversations", response_model=ConversationListResponse)
def get_all_conversations():
    return ConversationListResponse(
        conversations=conv_db.list_conversations()
    )

@router.post("/chat/new", response_model=ConversationCreateResponse)
def start_new_chat(payload: NewChatRequest):
    try:
        conversation = conv_db.create_conversation(
            user_id=payload.user_id,
            title=None,   # 🔥 NO title yet
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ConversationCreateResponse(
        conversation_id=conversation["id"],
        title=None,
        response=None,
    )



@router.post(
    "/conversations/{conversation_id}",
    response_model=ConversationCreateResponse,
)
def chat_with_docs(
    conversation_id: str,
    payload: ChatWithDocsRequest,
):
    if not payload.selected_documents:
        raise HTTPException(
            status_code=400,
            detail="No document selected for this query",
        )

    ai_response = process_user_query(
        conversation_id=conversation_id,
        user_query=payload.user_query,
        selected_documents=payload.selected_documents,
    )

    return ConversationCreateResponse(
        conversation_id=conversation_id,
        response=ai_response,
        title=conv_db.get_conversation(conversation_id)["title"],
    )


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
def get_conversation_history(conversation_id: str):
    if not conv_db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = conv_db.get_conversation_history(conversation_id)
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=[Message(id=m["id"], role=m["role"], text=m["content"]) for m in msgs],
    )


@router.delete("/conversations/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation(conversation_id: str):
    if not conv_db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_db.delete_conversation(conversation_id)
    return DeleteConversationResponse(conversation_id=conversation_id, deleted=True)


@router.get(
    "/conversations/{conversation_id}/documents",
    response_model=ConversationDocumentsResponse,
)
def list_conversation_documents(conversation_id: str):
    if not conv_db.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    docs = get_document_names(conversation_id)

    return ConversationDocumentsResponse(
        conversation_id=conversation_id,
        documents=docs,
    )

@router.post("/chat/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest):
    validate_feedback_rating(payload.rating)

    conversation = conv_db.get_conversation(payload.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = conv_db.get_message(payload.message_id)
    if not message or message["role"] != "ai":
        raise HTTPException(status_code=404, detail="AI message not found")

    conv_db.add_feedback(
        message_id=payload.message_id,
        user_id=conversation["user_id"],
        conversation_id=payload.conversation_id,
        rating=payload.rating,
    )

    return FeedbackResponse(
        message_id=payload.message_id,
        rating=payload.rating,
        status="feedback recorded",
    )