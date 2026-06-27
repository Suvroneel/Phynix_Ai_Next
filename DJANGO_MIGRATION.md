# Phynix Django — Migration Guide

## Structure

```
phynix_django/
├── accounts/           → Logout endpoint (auth = Supabase, same as before)
├── chat/               → Ashva chat + emotion + GenAI + RAG memory
│   └── services/
│       ├── emotion.py  ← mirrors Utils/model.py + emotion_responses.py
│       ├── genai.py    ← mirrors Utils/gen_ai.py (PhynixAI class)
│       ├── memory.py   ← mirrors Utils/memory.py (RAG pipeline)
│       └── db.py       ← Supabase DB calls for chat
├── dashboard/          → Home page: metrics, quote, Ashva insight, chart
├── diaries/            → Profile + Ashva Journal (page 3, same combined)
├── voice/              → NEW: Whisper transcription endpoint
├── static/
│   ├── css/phynix.css  ← ALL inline CSS from Streamlit, unified here
│   └── js/phynix-voice.js ← Mic button logic (Web Speech API + Whisper fallback)
└── templates/
    ├── base.html       ← Navbar, footer, HTMX, Chart.js
    ├── chat/
    │   ├── chat.html
    │   └── _message.html  ← HTMX partial
    ├── dashboard/home.html
    └── diaries/diary.html
```

## Environment Variables

```bash
DJANGO_SECRET_KEY=your-secret-key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
HF_TOKEN=hf_your_token
OPENAI_API_KEY=sk-...   # optional, for Whisper API fallback
```

## Local Setup

```bash
cd phynix_django
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Voice Input Flow

```
User clicks 🎤
    │
    ├─ Browser supports Web Speech API?
    │   └─ YES → transcribes live, drops text into textarea (no server needed)
    │
    └─ NO → records audio via MediaRecorder
           → POST audio to /voice/transcribe/
           → faster-whisper (local) OR OpenAI Whisper API
           → returns text, drops into textarea
```

## Key Design Decisions

- **HTMX for chat**: messages append without full page reload. No React needed.
- **Thin views**: views.py just wires request → service → template. No logic there.
- **One CSS file**: all the scattered `st.markdown("""<style>...""")` from Streamlit lives in `static/css/phynix.css`
- **Same Supabase**: no DB migration needed. Same tables, same schema.
- **Same color scheme**: `#ff914d` / `#ff6e40` gradient, Inter font, Montserrat for titles.
- **Page 3 stays combined**: profile + journal in one `diaries` app, faithful to the original.

## Requirements (add to requirements.txt)

```
django>=4.2
supabase>=2.0.0
pandas>=1.5.0
huggingface-hub>=0.19.0
sentence-transformers>=2.2.0
transformers>=4.30.0
torch>=2.0.0
faster-whisper>=0.10.0   # for voice (local)
```
