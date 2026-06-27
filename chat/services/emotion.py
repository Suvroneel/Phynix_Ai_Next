"""
chat/services/emotion.py
Wraps the BERT emotion model. Mirrors Utils/model.py + Utils/emotion_responses.py
"""
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_model():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained("Suvroneel/phynix-emotion-model")
    model = AutoModelForSequenceClassification.from_pretrained("Suvroneel/phynix-emotion-model")
    return tokenizer, model

def predict_emotion(text: str) -> str:
    import torch
    import torch.nn.functional as F
    tokenizer, model = _load_model()
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = F.softmax(logits, dim=1)
        predicted = torch.argmax(probs, dim=1).item()
    return model.config.id2label[predicted]

def get_risk_level(emotion_label: str) -> str:
    mapping = {
        "sadness": "High", "fear": "High", "anger": "High",
        "disgust": "Moderate", "neutral": "Neutral",
        "joy": "Low", "surprise": "Low",
    }
    return mapping.get(emotion_label.lower(), "Neutral")
