import random
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from supabase import create_client
import pandas as pd
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

FREE_ADVICE = [
    "You were born with a purpose. Rise up and fulfill your duty with courage.",
    "There is nothing lost or wasted in the journey of the soul. Every step counts.",
    "Even a little progress on the path of righteousness protects from great fear.",
    "When your mind is steady and undisturbed, nothing can shake your inner peace.",
    "Lift yourself by your own effort. Never underestimate your inner strength.",
    "The one who has conquered the self shines like a steady flame in a windless place.",
    "Stand firm in who you are. Your essence is divine and eternal.",
    "No effort in doing good is ever wasted. Trust the process.",
    "Awaken your inner power. Everything you need is already within you.",
    "Action is greater than inaction. Step forward with mindful effort.",
]

ASHVA_GUIDANCE = {
    "sadness": ["You've been feeling down. I'm here. Let's take it one step at a time.",
                "It's okay to feel heavy. You don't have to act like everything's fine."],
    "anger": ["You're frustrated, and that's totally okay. Let's take a deep breath together.",
              "Anger often protects something you care about. Wanna talk about it?"],
    "fear": ["Feeling worried? That's okay. Let's slow things down for a bit.",
             "Fear gets big when things feel uncertain. Let's focus on what you know right now."],
    "joy": ["You seem happy today! Hope you're enjoying that feeling.",
            "Hold onto what's making you smile. It's a good thing to keep close."],
    "neutral": ["Some days feel calm and quiet. That's okay — it's just space to breathe.",
                "You don't need to feel big emotions all the time. Quiet moments count too."],
    "disgust": ["Something really got to you, didn't it? Let's just take a moment to process.",
                "Let's step back from whatever's bothering you."],
    "surprise": ["Whoa, something caught you off guard! It's okay to still be sorting it out.",
                 "Surprises can shake things up. Let's take a second to see what's going on."],
}

EMOTION_LEVELS = {"joy": 6, "surprise": 5, "neutral": 4, "disgust": 3, "sadness": 2, "fear": 1, "anger": 0}

def _sb():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def _compute_metrics(user_name):
    try:
        sb = _sb()
        resp = sb.table("user_data").select("created_at,risks,predicted_emotion") \
            .eq("user_name", user_name).order("created_at", desc=True).limit(10).execute()
        if not resp.data or len(resp.data) < 2:
            return {"confidence": 0, "risk": 0, "mental_health": 0,
                    "confidence_delta": 0, "risk_delta": 0, "mental_delta": 0}
        df = pd.DataFrame(resp.data)
        df["risks"] = df["risks"].str.strip().str.lower()
        risk_map = {"low": 10, "moderate": 50, "neutral": 10, "high": 90}
        df["risk_val"] = df["risks"].map(risk_map).fillna(10)
        half = len(df) // 2
        prev, curr = df.iloc[half:], df.iloc[:half]
        p_risk, c_risk = prev["risk_val"].mean(), curr["risk_val"].mean()
        p_conf, c_conf = 100 - p_risk, 100 - c_risk
        p_mh = min(100, (p_conf + (100 - p_risk) / 2))
        c_mh = min(100, (c_conf + (100 - c_risk) / 2))
        def delta(c, p): return round(((c - p) / abs(p)) * 100, 1) if p else 0
        return {
            "confidence": round(c_conf), "risk": round(c_risk), "mental_health": round(c_mh),
            "confidence_delta": delta(c_conf, p_conf),
            "risk_delta": delta(c_risk, p_risk),
            "mental_delta": delta(c_mh, p_mh),
        }
    except Exception as e:
        print(f"Metrics error: {e}")
        return {"confidence": 0, "risk": 0, "mental_health": 0,
                "confidence_delta": 0, "risk_delta": 0, "mental_delta": 0}

def _today_emotions(user_name):
    try:
        sb = _sb()
        resp = sb.table("user_data").select("created_at,predicted_emotion") \
            .eq("user_name", user_name).execute()
        if not resp.data:
            return [], [], []
        df = pd.DataFrame(resp.data)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["date"] = df["created_at"].dt.date
        today = datetime.now(IST).date()
        df = df[df["date"] == today]
        df["predicted_emotion"] = df["predicted_emotion"].str.lower().str.strip()
        df = df[df["predicted_emotion"].isin(EMOTION_LEVELS)]
        df["val"] = df["predicted_emotion"].map(EMOTION_LEVELS)
        df = df.sort_values("created_at")
        labels = df["created_at"].dt.strftime("%I:%M %p").tolist()
        values = df["val"].tolist()
        names = df["predicted_emotion"].tolist()
        return labels, values, names
    except Exception as e:
        print(f"Today emotions error: {e}")
        return [], [], []

def _ashva_insight(user_name, user_email):
    try:
        sb = _sb()
        resp = sb.table("user_data").select("predicted_emotion") \
            .eq("user_name", user_name).eq("user_email", user_email) \
            .order("created_at", desc=True).limit(1).execute()
        if resp.data:
            emotion = resp.data[0]["predicted_emotion"].lower()
            options = ASHVA_GUIDANCE.get(emotion, ["Take a moment for yourself today."])
            return random.choice(options)
    except:
        pass
    return "Take a moment for yourself today. Your emotional well-being matters."

@login_required
def home(request):
    user = request.user
    metrics = _compute_metrics(user.username)
    labels, values, names = _today_emotions(user.username)
    insight = _ashva_insight(user.username, user.email)

    context = {
        "username": user.username,
        "daily_quote": random.choice(FREE_ADVICE),
        "metrics": metrics,
        "today_emotions": bool(labels),
        "today_emotion_labels": json.dumps(labels),
        "today_emotion_values": json.dumps(values),
        "today_emotion_names": json.dumps(names),
        "ashva_insight": insight,
    }
    return render(request, "dashboard/home.html", context)
