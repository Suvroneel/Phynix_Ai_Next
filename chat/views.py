from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from accounts.decorators import supabase_login_required
from datetime import datetime


def _get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    return "Good evening"


@supabase_login_required
def chat_view(request):
    messages = request.session.get("chat_messages", [])
    context = {
        "messages": messages,
        "greeting": _get_greeting(),
        "username": request.session.get("username", ""),
    }
    return render(request, "chat/chat.html", context)


@supabase_login_required
@require_POST
def send_message(request):
    from .services.emotion import predict_emotion, get_risk_level
    from .services.genai import PhynixAI
    from .services.memory import upsert_memory
    from .services.db import save_message

    email = request.session.get("user_email")
    username = request.session.get("username")
    text = request.POST.get("message", "").strip()
    if not text:
        return HttpResponse("")

    emotion_label = predict_emotion(text)
    risk_level = get_risk_level(emotion_label)

    session_msgs = request.session.get("chat_messages", [])
    chat_history = [
        {"role": "user" if m["sender"] == "user" else "assistant", "content": m["content"]}
        for m in session_msgs
    ]

    ai = PhynixAI()
    reply = ai.generate_response(
        user_message=text,
        detected_emotion=emotion_label,
        risk_level=risk_level,
        chat_history=chat_history,
        max_tokens=300,
        temperature=0.7,
    )

    save_message(user_email=email, user_name=username, message=text,
                 emotion=emotion_label, risk=risk_level, reply=reply)
    upsert_memory(text=text, user_email=email, user_name=username, source="chat")

    session_msgs.append({"sender": "user", "content": text})
    session_msgs.append({"sender": "bot", "content": reply, "emotion": emotion_label, "risk": risk_level})
    request.session["chat_messages"] = session_msgs
    request.session.modified = True

    user_html = render(request, "chat/_message.html", {"msg": {"sender": "user", "content": text}}).content.decode()
    bot_html = render(request, "chat/_message.html", {"msg": {"sender": "bot", "content": reply, "emotion": emotion_label, "risk": risk_level}}).content.decode()
    return HttpResponse(user_html + bot_html)


@supabase_login_required
@require_POST
def new_chat(request):
    request.session["chat_messages"] = []
    request.session.modified = True
    greeting = _get_greeting()
    username = request.session.get("username", "")
    html = f"""
    <div class="greeting-block fade-in">
      <h2>{greeting}, {username}</h2>
      <p>Welcome to <strong>Phynix</strong> — a space to reflect and share what you're feeling.<br/>
      I'm <strong>Ashva</strong>, your companion here.</p>
      <div class="prompt-chips">
        <button class="prompt-chip" data-text="Today, I'm feeling...">Today, I'm feeling...</button>
        <button class="prompt-chip" data-text="Lately, what's been bothering me is...">Lately, what's been bothering me is...</button>
        <button class="prompt-chip" data-text="Something that made me smile today was...">Something that made me smile today was...</button>
      </div>
    </div>"""
    return HttpResponse(html)
