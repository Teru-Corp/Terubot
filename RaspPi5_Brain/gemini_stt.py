# gemini_stt.py
import os
import wave
import tempfile
from typing import Optional

import pyaudio
from dotenv import load_dotenv
from google import genai

# ---- LOAD ENV ----
load_dotenv()

# ---- CONFIG ----
DEFAULT_MODEL = "gemini-2.5-flash"
CHUNK = 1024

# Your Logitech C270 from PyAudio list:
# 1 USB Device 0x46d:0x825: Audio (hw:3,0)
MIC_INDEX = 1


def record_wav(
    path: str,
    seconds: float = 4.0,
    sample_rate: int = 16000,
    device_index: Optional[int] = None,
):
    """Record mono 16-bit PCM WAV from microphone."""
    if device_index is None:
        device_index = MIC_INDEX

    pa = pyaudio.PyAudio()

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK,
    )

    frames = []
    num_chunks = int(sample_rate / CHUNK * seconds)

    for _ in range(num_chunks):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    stream.stop_stream()
    stream.close()
    pa.terminate()

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))


def transcribe(
    seconds: float = 4.0,
    sample_rate: int = 16000,
    device_index: Optional[int] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Record audio and return transcript text."""
    if device_index is None:
        device_index = MIC_INDEX

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found (check your .env)")

    client = genai.Client(api_key=api_key)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        record_wav(
            tmp.name,
            seconds=seconds,
            sample_rate=sample_rate,
            device_index=device_index,
        )
        audio_bytes = open(tmp.name, "rb").read()

    prompt = (
        "Transcribe the user's speech in this audio. "
        "Return ONLY the spoken text. "
        "If nothing is spoken, return an empty string."
    )

    response = client.models.generate_content(
        model=model,
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "audio/wav", "data": audio_bytes}},
                ],
            }
        ],
        config={"temperature": 0.0},
    )

    text = (response.text or "").strip()

    # Remove quotes if Gemini adds them
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1].strip()

    return text


def list_input_devices():
    """List available microphone input devices (PyAudio indices)."""
    pa = pyaudio.PyAudio()
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            devices.append((i, info["name"]))
    pa.terminate()
    return devices


if __name__ == "__main__":
    print("Available microphones:")
    for i, name in list_input_devices():
        print(f"{i}: {name}")

    print("\nSpeak now...")
    print("Transcript:", transcribe(seconds=4.0))
