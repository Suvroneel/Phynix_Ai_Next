"""
chat/services/genai.py
OpenRouter backend for Ashva. Same interface as before.
"""
import logging
from django.conf import settings
from openai import OpenAI, APIStatusError, APITimeoutError, APIConnectionError

log = logging.getLogger(__name__)

CRISIS_WORDS = (
    "kill myself", "suicide", "end my life", "want to die",
    "self harm", "self-harm", "hurt myself", "don't want to live",
)

CRISIS_REPLY = (
    "I am really glad you told me, and I am worried about you. "
    "Please reach out to someone right now. In India you can call Tele-MANAS at 14416. "
    "In the US you can call or text 988. If you are in immediate danger, "
    "call your local emergency number. I am here with you too."
)


def _is_crisis(text):
    t = text.lower()
    return any(w in t for w in CRISIS_WORDS)


class PhynixAI:
    SYSTEM_PROMPT = """You are Ashva, a compassionate AI companion within the Phynix mental health platform. Your role is to:
- Listen empathetically and validate emotions
- Provide supportive, non-judgmental responses
- Ask gentle follow-up questions when appropriate
- Never diagnose or provide medical advice
- Encourage professional help for serious concerns
- Keep responses conversational and warm (2-4 sentences typically)
- Use a caring, understanding tone"""

    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=12,
            max_retries=0,  # we do our own fallback, SDK retries only add delay
            default_headers={
                "HTTP-Referer": settings.SITE_URL,
                "X-Title": "Phynix",
            },
        )
        self.models = settings.OPENROUTER_MODELS

    def _call(self, model, messages, max_tokens, temperature):
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"reasoning": {"effort": "none"}},
        )
        return (resp.choices[0].message.content or "").strip()

    @staticmethod
    def _fold_system(messages):
        """For models that reject the system role."""
        system_text = messages[0]["content"]
        rest = [dict(m) for m in messages[1:]]
        for m in rest:
            if m["role"] == "user":
                m["content"] = f"{system_text}\n\n{m['content']}"
                break
        return rest

    def generate_response(self, user_message, detected_emotion=None, risk_level=None,
                          chat_history=None, max_tokens=300, temperature=0.7):
        if _is_crisis(user_message):
            return CRISIS_REPLY

        system = self.SYSTEM_PROMPT
        if detected_emotion and risk_level:
            system += (f"\n[Context: detected emotion is '{detected_emotion}' "
                       f"with {risk_level} risk. Respond with appropriate empathy.]")

        messages = [{"role": "system", "content": system}]
        messages.extend((chat_history or [])[-10:])  # keep prompts small on free tiers
        messages.append({"role": "user", "content": user_message})

        last_status = None
        for model in self.models:
            for msgs in (messages, self._fold_system(messages)):
                try:
                    reply = self._call(model, msgs, max_tokens, temperature)
                    if reply:
                        return reply
                    break  # empty reply, next model
                except APIStatusError as e:
                    last_status = e.status_code
                    log.warning("OpenRouter %s -> %s", model, e.status_code)
                    if e.status_code != 400:
                        break  # 429/403/404: next model
                    # 400: loop once more with the system prompt folded in
                except (APITimeoutError, APIConnectionError) as e:
                    last_status = "timeout"
                    log.warning("OpenRouter %s -> %s", model, type(e).__name__)
                    break

        if last_status == 429:
            return ("Ashva is getting a lot of visitors right now and needs a short breather. "
                    "Please try again in a few minutes, or write in the Ashva Diaries meanwhile.")
        return "Ashva is having a quiet moment. Please try again shortly."
