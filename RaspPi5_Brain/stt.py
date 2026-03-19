# stt.py
import queue
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from faster_whisper import WhisperModel

MIC_DEVICE_INDEX = 1
TARGET_SR = 16000
RECORD_SECONDS = 4
CHUNK_SIZE = 1280  # OK for OWW streaming


class VoiceIO_OWW:
    def __init__(
        self,
        wake_model_path="oww_models/hey_telloo.tflite",
        whisper_model_size="tiny.en",
        wake_threshold=0.5,
        cooldown_seconds=0.25,
        debug_scores=False,
    ):
        self.wake_threshold = float(wake_threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self.debug_scores = bool(debug_scores)

        # overflow reporting (NO PRINT in callback)
        self.overflow_count = 0
        self._last_overflow_print = time.time()

        print("🟡 Loading OpenWakeWord model...")
        self.oww = Model(wakeword_models=[wake_model_path])
        print("✅ OWW ready")

        print("🟡 Loading Whisper...")
        self.whisper = WhisperModel(
            whisper_model_size,
            device="cpu",
            compute_type="int8",
        )
        print("✅ Whisper ready")

        # Audio device setup
        self.device = MIC_DEVICE_INDEX
        try:
            device_info = sd.query_devices(self.device)
            default_sr = int(device_info["default_samplerate"])
            print(f"🟡 Using {device_info['name']} (default {default_sr} Hz)")
        except Exception as e:
            print(f"❌ Error accessing mic index {self.device}: {e}")
            raise

        # Try to force 16000 Hz if supported (reduces load a lot)
        forced_sr = None
        try:
            sd.check_input_settings(device=self.device, samplerate=TARGET_SR, channels=1)
            forced_sr = TARGET_SR
        except Exception:
            forced_sr = None

        self.device_sr = forced_sr if forced_sr else default_sr
        print(f"🟣 Input SR set to: {self.device_sr} Hz")

        # Bounded queue prevents runaway backlog
        self.q = queue.Queue(maxsize=60)

        self.stream = sd.RawInputStream(
            samplerate=self.device_sr,
            dtype="int16",
            channels=1,
            callback=self._callback,
            device=self.device,
            blocksize=CHUNK_SIZE,
            latency="low",
        )
        self.stream.start()

        # Decimation ratio (fast path if divisible)
        self.decim = None
        if self.device_sr % TARGET_SR == 0:
            self.decim = self.device_sr // TARGET_SR
            if self.decim != 1:
                print(f"✅ Fast decimation enabled: /{self.decim}")
        else:
            print("⚠️ device_sr not divisible by 16k; using linear resample fallback (slower).")

    # ---------- callback (must be FAST, no printing, no blocking) ----------
    def _callback(self, indata, frames, time_info, status):
        if status:
            self.overflow_count += 1

        b = bytes(indata)

        try:
            self.q.put_nowait(b)
        except queue.Full:
            # drop oldest to make room
            try:
                _ = self.q.get_nowait()
            except queue.Empty:
                pass
            try:
                self.q.put_nowait(b)
            except queue.Full:
                pass

    # ---------- helper: print overflow count occasionally (outside callback) ----------
    def maybe_print_overflows(self):
        now = time.time()
        if self.overflow_count > 0 and (now - self._last_overflow_print) > 2.0:
            print(f"⚠️ Audio overflow x{self.overflow_count} (last ~2s)")
            self.overflow_count = 0
            self._last_overflow_print = now

    def _resample_to_16k_int16(self, x_int16: np.ndarray) -> np.ndarray:
        """Convert input sample rate to 16kHz int16."""
        if self.decim is not None:
            return x_int16[::self.decim]

        # Linear interpolation fallback
        in_len = len(x_int16)
        out_len = int(in_len * (TARGET_SR / self.device_sr))
        if out_len <= 0:
            return np.array([], dtype=np.int16)

        return np.interp(
            np.linspace(0, in_len, out_len, endpoint=False),
            np.arange(in_len),
            x_int16
        ).astype(np.int16)

    def _flush_queue(self):
        """Drop any queued audio (use after wake detect)."""
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    def _collect_audio_for_whisper(self, seconds: float) -> np.ndarray:
        """Collect audio and returns float32 for Whisper (mono @16k)."""
        needed = int(seconds * TARGET_SR)
        chunks = []
        got = 0

        while got < needed:
            b = self.q.get()
            x16 = np.frombuffer(b, dtype=np.int16)
            x16_16k = self._resample_to_16k_int16(x16)
            if x16_16k.size == 0:
                continue
            chunks.append(x16_16k.astype(np.float32) / 32768.0)
            got += x16_16k.size

        return np.concatenate(chunks)[:needed]

    def listen_once(self) -> str:
        print("👂 Listening for wake word...")
        self.oww.reset()

        while True:
            self.maybe_print_overflows()

            try:
                b = self.q.get(timeout=1.0)
            except queue.Empty:
                continue

            x16 = np.frombuffer(b, dtype=np.int16)
            x16_16k = self._resample_to_16k_int16(x16)
            if x16_16k.size == 0:
                continue

            predictions = self.oww.predict(x16_16k)

            if self.debug_scores:
                best_name, best_score = max(predictions.items(), key=lambda kv: kv[1])
                rms = float(np.sqrt(np.mean(x16_16k.astype(np.float32) ** 2)))
                print(f"DEBUG best={best_name} {best_score:.3f} | RMS={rms:.1f}")

            for model_name, score in predictions.items():
                if score >= self.wake_threshold:
                    print(f"\n✅ WAKE WORD DETECTED: {model_name} ({score:.3f})")

                    time.sleep(self.cooldown_seconds)

                    # important: start command recording "now"
                    self._flush_queue()

                    print("🎙️ Recording command...")
                    audio_cmd = self._collect_audio_for_whisper(RECORD_SECONDS)

                    print("⚙️ Transcribing...")
                    segments, _ = self.whisper.transcribe(
                        audio_cmd,
                        language="en",
                        vad_filter=True,
                        beam_size=1,
                    )
                    text = "".join(seg.text for seg in segments).strip()
                    print(f"💬 Recognized: {text}")
                    return text

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


if __name__ == "__main__":
    v = VoiceIO_OWW(debug_scores=True)
    try:
        while True:
            command = v.listen_once()
            if "exit" in (command or "").lower():
                break
    finally:
        v.close()
