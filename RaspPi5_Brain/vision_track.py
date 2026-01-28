# vision_track.py
import cv2
import mediapipe as mp
import time

def run_tracking(robot_serial):
    """
    Runs face tracking and sends P:xx,T:yy to ESP32
    """
    pan = 90.0
    tilt = 90.0

    PAN_MIN, PAN_MAX = 20.0, 160.0
    TILT_MIN, TILT_MAX = 30.0, 150.0

    KP_PAN = 35.0
    KP_TILT = 28.0
    SMOOTH = 0.25
    DEADZONE = 0.03
    MIN_FACE_W_FRAC = 0.18   # tune for < ~1m

    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    mp_face = mp.solutions.face_detection
    detector = mp_face.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.6
    )

    last_send = 0.0
    SEND_DT = 1.0 / 25.0  # 25 Hz

    print("[VISION] Face tracking started")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = detector.process(rgb)

        have_target = False
        ex = ey = 0.0

        if res.detections:
            det = max(res.detections, key=lambda d: d.score[0])
            box = det.location_data.relative_bounding_box

            x = int(box.xmin * w)
            y = int(box.ymin * h)
            bw = int(box.width * w)
            bh = int(box.height * h)

            face_w_frac = bw / w

            if face_w_frac >= MIN_FACE_W_FRAC:
                cx = x + bw / 2.0
                cy = y + bh / 2.0

                ex = (cx - w/2) / w
                ey = (cy - h/2) / h
                have_target = True

        if have_target:
            if abs(ex) < DEADZONE: ex = 0
            if abs(ey) < DEADZONE: ey = 0

            target_pan = pan - ex * KP_PAN * 10
            target_tilt = tilt + ey * KP_TILT * 10

            target_pan = clamp(target_pan, PAN_MIN, PAN_MAX)
            target_tilt = clamp(target_tilt, TILT_MIN, TILT_MAX)

            pan = pan*(1-SMOOTH) + target_pan*SMOOTH
            tilt = tilt*(1-SMOOTH) + target_tilt*SMOOTH

        now = time.time()
        if now - last_send >= SEND_DT:
            last_send = now
            msg = f"P:{pan:.1f},T:{tilt:.1f}\n"

            # IMPORTANT: you need this function in serial_com
            robot_serial.send_raw(msg)

        time.sleep(0.01)
