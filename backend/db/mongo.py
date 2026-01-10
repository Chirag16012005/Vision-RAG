import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

import os
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

client: Optional[MongoClient] = None
db = None

conversations_col: Optional[Collection] = None
messages_col: Optional[Collection] = None
summaries_col: Optional[Collection] = None
conversation_documents_col: Optional[Collection] = None
feedbacks_col: Optional[Collection] = None


def connect() -> bool:
    """Attempt to (re)establish the MongoDB connection."""
    global client, db
    global conversations_col, messages_col, summaries_col, conversation_documents_col, feedbacks_col

    if client is not None and all(
        coll is not None
        for coll in (conversations_col, messages_col, conversation_documents_col, summaries_col, feedbacks_col)
    ):
        return True

    if not MONGO_URI or not MONGO_DB:
        print("❌ MongoDB configuration missing. Check MONGO_URI and MONGO_DB environment variables.")
        return False

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")

        db = client[MONGO_DB]

        conversations_col = db.get_collection("conversations")
        messages_col = db.get_collection("messages")
        summaries_col = db.get_collection("conversation_summaries")
        conversation_documents_col = db.get_collection("conversation_documents")
        feedbacks_col = db.get_collection("feedbacks")

        print("✅ MongoDB connected successfully")
        print("Target DB:", MONGO_DB)
        print("Collections:", db.list_collection_names())
        return True

    except ServerSelectionTimeoutError as e:
        print("❌ MongoDB connection failed:", e)
        client = None
        db = None
        conversations_col = None
        messages_col = None
        summaries_col = None
        conversation_documents_col = None
        feedbacks_col = None
        return False


def ensure_connection() -> bool:
    """Public helper for downstream modules to guarantee Mongo availability."""
    return connect()


# Attempt initial connection during import so existing behaviour remains similar.
connect()