from serial_com import SerialController
import threading
import vision
from idle_anim import IdleAnimator
from sounds import SoundPlayer

# TEMP: replace with /dev/serial/by-id/... later
EYE_PORTS   = ["/dev/ttyACM1", "/dev/ttyACM2"]
MOTOR_PORTS = ["/dev/ttyACM0"]

eyes_serial   = SerialController(EYE_PORTS, name="EYES")
motors_serial = SerialController(MOTOR_PORTS, name="MOTORS")

tracking_thread = None
idle_thread = None
idle_anim = None

# ---- ROUTING RULES ----
EYES_ONLY  = {"B"}     # gaze
BOTH       = {"H","S","L","R","U","D","C","V"}             # example: emotion affects both
MOTORS_ONLY = {"N","Y","Q"}                    # fill if you have motor-only single letters

sound = SoundPlayer(
	sound_dir="/home/terubot/terubot_brain/sounds",
	device="plughw:2,0"
)

def send_routed(cmd: str):
    """
    cmd can be:
      - single letter: "H"
      - a line: "B 80"
    """
    s = cmd.strip()
    if not s:
        return

    up = s.upper()

    # Blink is eyes-only (and often multi-token like "B 80")
    if up.startswith("B"):
        eyes_serial.send_raw_line(up)
        return

    # Single-letter routing
    if len(up) == 1:
        if up in BOTH:
            eyes_serial.send_char(up)
            motors_serial.send_char(up)
            return
        if up in EYES_ONLY:
            eyes_serial.send_char(up)
            return
        if up in MOTORS_ONLY:
            motors_serial.send_char(up)
            return

    # If you have motor words like "MFWD", route here:
    # motors_serial.send_raw_line(up)

    print("Unknown command:", cmd)

def start_tracking():
    global tracking_thread
    # keep idle for eyes (so eyes don't move if your idle only does blink)
    if idle_anim:
        idle_anim.set_mode(idle=False, blink=True)

    if tracking_thread is None or not tracking_thread.is_alive():
        tracking_thread = threading.Thread(
            target=vision.run_tracking,
            args=(motors_serial,),   # tracking controls ONLY motors
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

def start():
    print("\nTERUBOT TERMINAL CONTROL")
    print("Type: H S N L R U D C B or 'B 80'")
    print("Type: track on  → start face tracking")
    print("Type: quit      → exit\n")

    start_idle()
    start_tracking()

    try:
        while True:
            msg = input("CMD> ").strip()

            if msg.lower() == "quit":
                break

            if msg.lower() == "track on":
                start_tracking()
                continue
            if msg.lower() == "track debug":
                # run in main thread so cv2.imshow works
                if idle_anim:
                   idle_anim.set_mode(idle=True, blink=True)
                vision.run_tracking(motors_serial)
                continue


            # allow typing "H S L" etc.
            parts = msg.replace(",", " ").split()
            for p in parts:
                # If user sends manual gaze/expression, stop idle gaze from overwriting eyes
                if idle_anim:
                    idle_anim.notify_manual(p)  # safe even if cmd is BOTH
                send_routed(p)
                sound.play_for_cmd(p)

    except KeyboardInterrupt:
        pass
    finally:
        if idle_anim:
            idle_anim.stop()
        eyes_serial.close()
        motors_serial.close()
        print("Closed.")

if __name__ == "__main__":
    start()
