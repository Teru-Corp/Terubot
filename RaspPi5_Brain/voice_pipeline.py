# voice_pipeline.py
import time
from typing import Callable, Optional

from emotion_map import emotion_to_cmd

class VoicePipeline:
    """
    Glue layer:
      audio -> transcript (gemini_stt)
      transcript -> emotion (gemini_emotion)
      emotion -> robot command (H/S/N...)
    """

    def __init__(
        self,
        stt_module,
        emo_module,
        record_seconds: float = 4.0,
        cooldown_s: float = 0.8,
        min_chars: int = 3,
    ):
        self.stt = stt_module
        self.emo = emo_module
        self.record_seconds = record_seconds
        self.cooldown_s = cooldown_s
        self.min_chars = min_chars
        self._last_run = 0.0

    def run_once(self):
        # simple rate limit so you don't spam API
        now = time.time()
        if now - self._last_run < self.cooldown_s:
            return None
        self._last_run = now

        # ---- 1) Speech to text ----
        # CHANGE THIS LINE if your function name differs:
        text = self.stt.transcribe(seconds=self.record_seconds)

        if not text:
            return None
        text = text.strip()
        if len(text) < self.min_chars:
            return None

        # ---- 2) Emotion ----
        # CHANGE THIS LINE if your function name differs:
        emo = self.emo.classify(text)  # expects dict with label/confidence

        label = emo.get("label", "neutral")
        conf = float(emo.get("confidence", 0.5))

        # ---- 3) Map to robot command ----
        cmd = emotion_to_cmd(label, conf)

        return {"text": text, "emotion": emo, "cmd": cmd}
