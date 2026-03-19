# main.py
from serial_com import SerialController
from i2c_com import I2CController
import threading
import queue
import time
import sys
import select

import vision
from idle_anim import IdleAnimator
from sounds import SoundPlayer

from stt import VoiceIO_OWW
from llm_emotion import process_text


# ------------------- PORTS -------------------
# TEMP: replace with /dev/serial/by-id/... later
EYE_TRANSPORT = "i2c"  # "i2c" or "serial"
EYE_PORTS = ["/dev/ttyAMA2", "/dev/ttyAMA0"]
EYE_I2C_TARGETS = [
    (1, 0x10),
    (1, 0x11),
]
MOTOR_PORTS = ["/dev/ttyACM0"]

def build_eyes_controller():
    transport = EYE_TRANSPORT.strip().lower()

    if transport == "i2c":
        return I2CController(EYE_I2C_TARGETS, name="EYES")

    if transport == "serial":
        return SerialController(EYE_PORTS, name="EYES")

    raise ValueError(f"Unsupported eye transport: {EYE_TRANSPORT}")


eyes_serial = build_eyes_controller()
motors_serial = SerialController(MOTOR_PORTS, name="MOTORS")
EYES_LINK_LABEL = "I2C" if EYE_TRANSPORT.strip().lower() == "i2c" else "SERIAL"

# ------------------- THREAD STATE -------------------
tracking_thread = None
idle_thread = None
idle_anim = None

voice_thread = None
voice_stop = threading.Event()
voice_events = queue.Queue()  # transcripts from STT

# Tracking pause so gestures aren't overwritten by face tracking
tracking_pause = threading.Event()


# ------------------- ROUTING RULES -------------------
EYES_ONLY = {"BLINK"}  # blink + confused face on eyes only
BOTH = {"HAPPY", "SAD", "RIGHT", "UP", "DOWN", "CENTER", "LEFT"}  # expressions affecting both
MOTORS_ONLY = {"NO", "YES", "QUESTION"}  # yes/no/question motions (motors only)


sound = SoundPlayer(
    sound_dir="/home/terubot/terubot_brain/sounds",
    device="plughw:2,0",
)


# ------------------- MOTORS PROXY (blocks tracking writes during gestures) -------------------
class MotorsProxy:
    """
    This proxy is passed to vision.run_tracking().
    When tracking_pause is set, any motor commands from tracking are ignored.
    """
    def __init__(self, inner: SerialController, pause_event: threading.Event):
        self.inner = inner
        self.pause_event = pause_event

    def send_command(self, cmd: str):
        if self.pause_event.is_set():
            return
        return self.inner.send_command(cmd)

    def send_raw_line(self, line: str):
        if self.pause_event.is_set():
            return
        return self.inner.send_raw_line(line)

    def close(self):
        return self.inner.close()


motors_proxy = MotorsProxy(motors_serial, tracking_pause)


def send_routed(cmd: str):
    """
    Routes full-word commands to appropriate serial controllers.
    cmd examples: "HAPPY", "BLINK", "BLINK 80", "LEFT", etc.
    """
    s = cmd.strip()
    if not s:
        return

    up = s.upper()
    
    # Extract the base command (first word)
    base_cmd = up.split()[0] if ' ' in up else up

    # Blink commands (can have parameters like "BLINK 80")
    if base_cmd == "BLINK":
        print(f"➡️  {EYES_LINK_LABEL} EYES   <= {up!r}")
        eyes_serial.send_raw_line(up)
        return

    # Commands that affect both eyes and motors
    if base_cmd in BOTH:
        print(f"➡️  {EYES_LINK_LABEL} EYES   <= {up!r}")
        print(f"➡️  SERIAL MOTORS <= {up!r}")
        eyes_serial.send_command(up)
        motors_serial.send_command(up)
        return

    # Eyes-only commands
    if base_cmd in EYES_ONLY:
        print(f"➡️  {EYES_LINK_LABEL} EYES   <= {up!r}")
        eyes_serial.send_command(up)
        return

    # Motors-only commands (pause tracking during gestures)
    if base_cmd in MOTORS_ONLY:
        print(f"➡️  SERIAL MOTORS <= {up!r}  (pause tracking)")
        tracking_pause.set()
        try:
            motors_serial.send_command(up)
            # Give the gesture time to play
            time.sleep(0.8)
        finally:
            tracking_pause.clear()
        return

    print("❓ Unknown command:", cmd)


def start_tracking():
    global tracking_thread

    # Tracking only drives motors, so keep eye idle + blink active.
    if idle_anim:
        idle_anim.set_mode(idle=True, blink=True)

    if tracking_thread is None or not tracking_thread.is_alive():
        tracking_thread = threading.Thread(
            target=vision.run_tracking,
            args=(motors_proxy,),  # tracking controls ONLY motors (through proxy)
            daemon=True
        )
        tracking_thread.start()
        print("TRACKING ON (MOTORS)")


def start_idle():
    global idle_thread, idle_anim

    if idle_anim is None:
        idle_anim = IdleAnimator(eyes_serial)  # idle controls ONLY eyes

    if idle_thread is None or not idle_thread.is_alive():
        idle_thread = threading.Thread(target=idle_anim.run, daemon=True)
        idle_thread.start()
        print("IDLE ANIMATOR ON")


# ------------------- VOICE LOOP -------------------
def _voice_loop():
    """
    Always:
      wake -> whisper -> push transcript into voice_events queue
    """
    stt = VoiceIO_OWW(
        wake_model_path="oww_models/hey_telloo.tflite",
        whisper_model_size="tiny.en",
        wake_threshold=0.6,
        cooldown_seconds=0.35,
        debug_scores=False,
    )

    try:
        while not voice_stop.is_set():
            text = stt.listen_once()
            if text and text.strip():
                voice_events.put(text.strip())
            else:
                time.sleep(0.05)
    except Exception as e:
        print("VOICE LOOP ERROR:", e)
    finally:
        stt.close()


def start_voice():
    global voice_thread
    if voice_thread is None or not voice_thread.is_alive():
        voice_stop.clear()
        voice_thread = threading.Thread(target=_voice_loop, daemon=True)
        voice_thread.start()
        print("VOICE ON (OWW + Whisper)")


def stop_voice():
    voice_stop.set()
    print("VOICE OFF")


# ------------------- LLM HANDLER -------------------
def handle_user_text(user_text: str):
    """
    Runs your Ollama emotion LLM, then routes the resulting cmd_code
    to eyes/motors + plays sound.

    Special rule:
      If cmd_code == QUESTION (unclear/unsure), also send LEFT to eyes first.
    """
    user_text = user_text.strip()
    if not user_text:
        return

    print(f"\n🗣️ USER: {user_text}")

    reply, cmd_code = process_text(user_text)
    cmd_code = (cmd_code or "QUESTION").strip().upper()

    # safety: if weird cmd, treat as unsure
    if cmd_code not in {"HAPPY", "SAD", "YES", "NO", "CENTER"}:
        cmd_code = "QUESTION"

    print(f"🤖 TERUBOT: {reply}")
    print(f"🧠 EMOTION/CMD: {cmd_code}")

    # If unsure → show confusion eyes + question motion
    if cmd_code == "QUESTION":
        print("⚠️ Unsure/unclear → sending LEFT (eyes) + QUESTION (motors)")
        if idle_anim:
            idle_anim.notify_manual("LEFT")
        send_routed("LEFT")
        sound.play_for_cmd("LEFT")
        time.sleep(0.05)

    # Prevent idle overwriting the expression
    if idle_anim:
        idle_anim.notify_manual(cmd_code)

    send_routed(cmd_code)
    sound.play_for_cmd(cmd_code)


# ------------------- MAIN -------------------
def start():
    print("\nTERUBOT CONTROL")
    print("- Voice: say wake word to talk")
    print("- Keyboard: type commands or text")
    print("\nCommands:")
    print("  track on      → start face tracking (threaded)")
    print("  track debug   → run tracking in main thread (cv2.imshow)")
    print("  voice on/off  → enable/disable voice loop")
    print("  quit          → exit")
    print("\nSupported commands: HAPPY, SAD, LEFT, RIGHT, UP, DOWN, CENTER, BLINK, NO, YES, QUESTION\n")

    start_idle()
    start_tracking()
    start_voice()

    try:
        while True:
            # 1) Handle ALL pending voice events first (non-blocking)
            handled_any = False
            while True:
                try:
                    vt = voice_events.get_nowait()
                except queue.Empty:
                    break

                handled_any = True
                print(f"\n🎤 VOICE EVENT: {vt}")
                handle_user_text(vt)

            # 2) Non-blocking keyboard input (Linux)
            if not handled_any:
                print("CMD/TEXT> ", end="", flush=True)

            r, _, _ = select.select([sys.stdin], [], [], 0.15)  # 150ms tick
            if not r:
                continue

            msg = sys.stdin.readline().strip()
            if not msg:
                continue

            low = msg.lower()

            if low == "quit":
                break

            if low == "track on":
                start_tracking()
                continue

            if low == "track debug":
                if idle_anim:
                    idle_anim.set_mode(idle=True, blink=True)
                vision.run_tracking(motors_proxy)
                continue

            if low == "voice on":
                start_voice()
                continue

            if low == "voice off":
                stop_voice()
                continue

            parts = msg.replace(",", " ").split()

            # Check if it's a recognized command word
            if parts:
                first_word = parts[0].upper()
                
                # Handle BLINK with optional parameter
                if first_word == "BLINK":
                    cmd_line = "BLINK" if len(parts) == 1 else f"BLINK {parts[1]}"
                    if idle_anim:
                        idle_anim.notify_manual("BLINK")
                    send_routed(cmd_line)
                    sound.play_for_cmd("BLINK")
                    continue
                
                # Check if it's a recognized command
                all_commands = BOTH | EYES_ONLY | MOTORS_ONLY
                if first_word in all_commands:
                    if idle_anim:
                        idle_anim.notify_manual(first_word)
                    send_routed(first_word)
                    sound.play_for_cmd(first_word)
                    continue

            # Otherwise treat as natural language → LLM
            handle_user_text(msg)

    except KeyboardInterrupt:
        pass

    finally:
        stop_voice()
        if idle_anim:
            idle_anim.stop()
        eyes_serial.close()
        motors_serial.close()
        print("Closed.")


if __name__ == "__main__":
    start()
