# emotion_map.py
def emotion_to_cmd(label: str, confidence: float) -> str:
    label = (label or "neutral").lower()

    if confidence < 0.55:
        return "N"

    if label in ("joy", "calm", "surprise"):
        return "H"
    if label in ("sadness", "fear", "disgust"):
        return "S"
    if label in ("anger", "stress"):
        return "S"   # later you can add a dedicated "A"
    return "N"
