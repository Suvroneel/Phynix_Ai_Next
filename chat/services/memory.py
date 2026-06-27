"""
chat/services/memory.py — mirrors Utils/memory.py
"""
import uuid
from django.conf import settings
from supabase import create_client

def _get_supabase():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def _get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

def upsert_memory(text: str, user_email: str, user_name: str, source: str):
    try:
        embedder = _get_embedder()
        vector = embedder.encode(text).tolist()
        sb = _get_supabase()
        sb.table("memory_embeddings").upsert({
            "id": str(uuid.uuid4()),
            "user_email": user_email,
            "user_name": user_name,
            "source": source,
            "text": text,
            "embedding": vector,
        }).execute()
    except Exception as e:
        print(f"Memory upsert error: {e}")

def retrieve_memories(query: str, user_email: str, top_k: int = 4):
    try:
        embedder = _get_embedder()
        vector = embedder.encode(query).tolist()
        sb = _get_supabase()
        resp = sb.rpc("match_memories", {
            "query_embedding": vector,
            "match_user_email": user_email,
            "match_count": top_k,
        }).execute()
        return resp.data
    except Exception as e:
        print(f"Memory retrieve error: {e}")
        return []
