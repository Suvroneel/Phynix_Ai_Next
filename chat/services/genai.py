"""
chat/services/genai.py — mirrors Utils/gen_ai.py
"""
from django.conf import settings

class PhynixAI:
    SYSTEM_PROMPT = """You are Ashva, a compassionate AI companion within the Phynix mental health platform. Your role is to:
- Listen empathetically and validate emotions
- Provide supportive, non-judgmental responses
- Ask gentle follow-up questions when appropriate
- Never diagnose or provide medical advice
- Encourage professional help for serious concerns
- Keep responses conversational and warm (2-4 sentences typically)"""

    def __init__(self):
        from huggingface_hub import InferenceClient
        token = getattr(settings, "HF_TOKEN", None)
        self.client = InferenceClient(token=token)
        self.model = "meta-llama/Llama-3.1-8B-Instruct"

    def generate_response(self, user_message, detected_emotion=None,
                          risk_level=None, chat_history=None,
                          max_tokens=300, temperature=0.7):
        try:
            ctx = ""
            if detected_emotion and risk_level:
                ctx = f"\n[Context: emotion='{detected_emotion}', risk={risk_level}. Respond with appropriate empathy.]"
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT + ctx}]
            if chat_history:
                messages.extend(chat_history)
            messages.append({"role": "user", "content": user_message})
            resp = self.client.chat_completion(
                model=self.model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "rate limit" in err.lower():
                return "I'm experiencing high demand right now. Could you try again in a moment?"
            return f"I'm having a technical issue. Please try again."
