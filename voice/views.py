"""
voice/views.py — Whisper transcription endpoint
Called by phynix-voice.js when Web Speech API is unavailable.
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.decorators import supabase_login_required
from django.conf import settings


@supabase_login_required
@require_POST
def transcribe(request):
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "No audio file provided."}, status=400)

    try:
        # faster-whisper (local) — change to OpenAI Whisper API if preferred
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_file, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        return JsonResponse({"text": text})
    except ImportError:
        # Fallback: try OpenAI Whisper API
        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            audio_file.seek(0)
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.webm", audio_file.read(), "audio/webm"),
            )
            return JsonResponse({"text": transcript.text})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
