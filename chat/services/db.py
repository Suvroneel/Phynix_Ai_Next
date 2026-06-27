"""
chat/services/db.py — Supabase database operations for chat
"""
from django.conf import settings
from supabase import create_client

def _sb():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def save_message(user_email, user_name, message, emotion, risk, reply):
    try:
        sb = _sb()
        count = sb.table("user_data").select("index", count="exact").execute().count or 0
        sb.table("user_data").insert({
            "index": count + 1,
            "user_email": user_email,
            "user_name": user_name,
            "messages": message,
            "predicted_emotion": emotion,
            "risks": risk,
            "replies": reply,
        }).execute()
    except Exception as e:
        print(f"DB save_message error: {e}")

def get_chat_history(user_email: str, limit: int = 20) -> list:
    try:
        sb = _sb()
        resp = sb.table("user_data").select("messages,replies,predicted_emotion,risks") \
            .eq("user_email", user_email) \
            .order("created_at", desc=True).limit(limit).execute()
        msgs = []
        for row in reversed(resp.data or []):
            if row.get("messages"):
                msgs.append({"sender": "user", "content": row["messages"]})
            if row.get("replies"):
                msgs.append({
                    "sender": "bot",
                    "content": row["replies"],
                    "emotion": row.get("predicted_emotion", ""),
                    "risk": row.get("risks", ""),
                })
        return msgs
    except Exception as e:
        print(f"DB get_chat_history error: {e}")
        return []
