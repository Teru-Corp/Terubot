# gemini_emotion.py
import os
import json
from typing import Dict, Any

from dotenv import load_dotenv
from google import genai

# ---- LOAD ENV ----
load_dotenv()

# ---- EMOTION SET ----
ALLOWED = [
    "joy",
    "sadness",
    "anger",
    "fear",
    "disgust",
    "surprise",
    "neutral",
    "stress",
    "calm",
]

SYSTEM_PROMPT = (
    "You are an emotion classifier for short spoken utterances to a small social robot. "
    "Return ONLY valid JSON with keys:\n"
    '{'
    '"label": one of '
    + str(ALLOWED)
    + ', '
    '"confidence": number between 0 and 1, '
    '"valence": number between -1 and 1, '
    '"arousal": number between 0 and 1'
    '}\n'
    "No extra text. No markdown."
)


def _safe_json(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        t = t.replace("json", "", 1).strip()
    return json.loads(t)


def classify(text: str, model: str = "gemini-2.5-flash") -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=[
            {"role": "system", "parts": [{"text": SYSTEM_PROMPT}]},
            {"role": "user", "parts": [{"text": f'Utterance: "{text}"'}]},
        ],
        config={"temperature": 0.2},
    )

    data = _safe_json(response.text)

    label = str(data.get("label", "neutral")).lower().strip()
    if label not in ALLOWED:
        label = "neutral"

    def clamp(x, lo, hi, default):
        try:
            return max(lo, min(hi, float(x)))
        except Exception:
            return default

    return {
        "label": label,
        "confidence": clamp(data.get("confidence"), 0.0, 1.0, 0.5),
        "valence": clamp(data.get("valence"), -1.0, 1.0, 0.0),
        "arousal": clamp(data.get("arousal"), 0.0, 1.0, 0.5),
    }


if __name__ == "__main__":
    while True:
        t = input("text> ").strip()
        if not t:
            continue
        print(classify(t))
