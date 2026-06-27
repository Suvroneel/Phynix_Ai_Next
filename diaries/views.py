import random
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from django.shortcuts import render, redirect
from accounts.decorators import supabase_login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from supabase import create_client

IST = ZoneInfo("Asia/Kolkata")

DIARY_PLACEHOLDERS = [
    "Write whatever feels right, even if it's just one line.",
    "You can write anything that feels like you, even if it's just a single thought.",
    "Still empty. Write what feels right, even if it's small.",
    "No words yet. This space is yours when you feel like speaking.",
    "Nothing here yet. When you're ready, say something that feels true.",
]

def _sb():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def _fetch_today_entries(user_name):
    try:
        today_midnight = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        resp = _sb().table("mood_journal").select("*") \
            .eq("user_name", user_name).gte("created_at", today_midnight) \
            .order("created_at", desc=True).execute()
        entries = resp.data or []
        for e in entries:
            try:
                dt = datetime.fromisoformat(e["created_at"]).astimezone(IST)
                e["created_at_ist"] = dt.strftime("%d %b %Y, %I:%M %p")
            except:
                e["created_at_ist"] = e["created_at"]
        return entries
    except Exception as ex:
        print(f"fetch entries error: {ex}")
        return []

def _get_bio(user_name):
    try:
        resp = _sb().table("user_bio").select("user_description") \
            .eq("user_name", user_name).order("created_at", desc=True).limit(1).execute()
        return resp.data[0]["user_description"] if resp.data else ""
    except:
        return ""

@supabase_login_required
def diary_view(request):
    email = request.session.get("user_email")
    username = request.session.get("username", "")
    show_entries = request.GET.get("clear") != "1"
    profile_image = request.session.get("profile_image", "")
    bio = _get_bio(username)
    entries = _fetch_today_entries(username) if show_entries else []

    context = {
        "username": username,
        "profile_image": profile_image,
        "bio": bio,
        "entries": entries,
        "show_entries": show_entries,
        "diary_placeholder": random.choice(DIARY_PLACEHOLDERS),
        "avatar_range": [str(i) for i in range(1, 10)],
    }
    return render(request, "diaries/diary.html", context)

@supabase_login_required
@require_POST
def save_entry(request):
    email = request.session.get("user_email")
    username = request.session.get("username", "")
    entry_text = request.POST.get("entry", "").strip()
    if not entry_text:
        return redirect("diaries:diary")

    image_url = None
    image_file = request.FILES.get("image")
    if image_file:
        try:
            sb = _sb()
            ext = image_file.name.split(".")[-1]
            path = f"{username}/{uuid.uuid4().hex}.{ext}"
            sb.storage.from_("journal-images").upload(path, image_file.read(), {"content-type": image_file.content_type})
            image_url = sb.storage.from_("journal-images").get_public_url(path)
        except Exception as e:
            print(f"Image upload error: {e}")

    try:
        _sb().table("mood_journal").insert({
            "user_name": username,
            "user_email": email,
            "entry": entry_text,
            "image_url": image_url,
        }).execute()
    except Exception as e:
        print(f"Insert entry error: {e}")

    # RAG memory
    try:
        from chat.services.memory import upsert_memory
        upsert_memory(text=entry_text, user_email=email, user_name=username, source="diary")
    except:
        pass

    return redirect("diaries:diary")

@supabase_login_required
@require_POST
def update_bio(request):
    email = request.session.get("user_email")
    username = request.session.get("username", "")
    bio = request.POST.get("bio", "").strip()
    try:
        sb = _sb()
        count = sb.table("user_bio").select("id", count="exact").execute().count or 0
        sb.table("user_bio").insert({
            "id": count + 1,
            "user_name": username,
            "user_description": bio,
        }).execute()
    except Exception as e:
        print(f"Bio update error: {e}")
    return redirect("diaries:diary")

@supabase_login_required
@require_POST
def set_avatar(request):
    avatar_num = request.POST.get("avatar", "1")
    request.session["profile_image"] = f"/static/images/profiles/profile{avatar_num}.png"
    request.session.modified = True
    return redirect("diaries:diary")
