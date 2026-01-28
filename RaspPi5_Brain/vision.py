import time
import cv2
import mediapipe as mp

# -------- CONFIG --------
CAM_INDEX = 0
ROTATE_90 = "CW"  # "CW", "CCW", or None

MODE = "AUTO"     # "FACE", "HAND", or "AUTO" (hand preferred)

SEND_HZ = 12
SMOOTH = 0.12
DEADZONE = 0.03
LOST_TIMEOUT = 0.45

GAIN_PAN = 80.0
GAIN_TILT = 60.0

PAN_MAX = 30.0
TILT_MAX = 20.0

MAX_STEP_PAN = 6.0
MAX_STEP_TILT = 0.7

SHOW_DEBUG = True
# ------------------------


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def approach(current, target, max_step):
    if target > current + max_step:
        return current + max_step
    if target < current - max_step:
        return current - max_step
    return target


def run_tracking(motors_serial):
    print(f"[vision] Tracking ON (motors) mode={MODE}")

    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 540)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

    if not cap.isOpened():
        print("[vision] ERROR: camera not opened")
        return

    # Face
    mp_face = mp.solutions.face_detection
    face = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.6)

    # Hands (lighter weight)
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )

    pan_f = 0.0
    tilt_f = 0.0
    last_seen_time = time.time()

    period = 1.0 / float(SEND_HZ)
    last_send = 0.0

    fps = 0.0
    t_prev = time.time()

    if SHOW_DEBUG:
        cv2.namedWindow("TeruBot Vision (DEBUG)", cv2.WINDOW_NORMAL)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            if ROTATE_90 == "CW":
               frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif ROTATE_90 == "CCW":
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            found = False
            pan_target = 0.0
            tilt_target = 0.0
            src = "LOST"

            # ---------- HAND TRACK ----------
            hand_cx = hand_cy = None
            if MODE in ("HAND", "AUTO"):
                res_h = hands.process(rgb)
                if res_h.multi_hand_landmarks:
                    lm = res_h.multi_hand_landmarks[0].landmark
                    # Index fingertip (8). If you want "palm", use wrist (0).
                    pt = lm[8]
                    hand_cx = float(pt.x)
                    hand_cy = float(pt.y)

            # ---------- FACE TRACK ----------
            face_cx = face_cy = None
            if MODE in ("FACE", "AUTO"):
                res_f = face.process(rgb)
                if res_f.detections:
                    # pick first/best
                    det = res_f.detections[0]
                    box = det.location_data.relative_bounding_box
                    face_cx = box.xmin + box.width * 0.5
                    face_cy = box.ymin + box.height * 0.5

            # Choose what to follow
            cx = cy = None
            if MODE == "HAND":
                cx, cy = hand_cx, hand_cy
                src = "HAND"
            elif MODE == "FACE":
                cx, cy = face_cx, face_cy
                src = "FACE"
            else:
                # AUTO: prefer hand if present
                if hand_cx is not None:
                    cx, cy = hand_cx, hand_cy
                    src = "HAND"
                elif face_cx is not None:
                    cx, cy = face_cx, face_cy
                    src = "FACE"

            if cx is not None and cy is not None:
                errx = cx - 0.5
                erry = cy - 0.5

                if abs(errx) < DEADZONE:
                    errx = 0.0
                if abs(erry) < DEADZONE:
                    erry = 0.0

                pan_target = -errx * GAIN_PAN
                tilt_target = -erry * GAIN_TILT

                pan_target = clamp(pan_target, -PAN_MAX, PAN_MAX)
                tilt_target = clamp(tilt_target, -TILT_MAX, TILT_MAX)

                found = True
                last_seen_time = time.time()
            else:
                src = "LOST"

            if (not found) and (time.time() - last_seen_time > LOST_TIMEOUT):
                pan_target = 0.0
                tilt_target = 0.0

            # rate limit + smooth
            pan_target = approach(pan_f, pan_target, MAX_STEP_PAN)
            tilt_target = approach(tilt_f, tilt_target, MAX_STEP_TILT)

            pan_f += (pan_target - pan_f) * SMOOTH
            tilt_f += (tilt_target - tilt_f) * SMOOTH

            # send
            now = time.time()
            if now - last_send >= period:
                last_send = now
                motors_serial.send_raw_line(f"T,{pan_f:.1f},{tilt_f:.1f}")

            # debug draw
            if SHOW_DEBUG:
                # crosshair
                cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)
                cv2.line(frame, (0, h // 2), (w, h // 2), (255, 255, 255), 1)

                if hand_cx is not None:
                    cv2.circle(frame, (int(hand_cx * w), int(hand_cy * h)), 7, (255, 255, 255), -1)
                if face_cx is not None:
                    cv2.circle(frame, (int(face_cx * w), int(face_cy * h)), 7, (255, 255, 255), 2)

                t_now = time.time()
                dt = t_now - t_prev
                t_prev = t_now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)

                cv2.putText(
                    frame,
                    f"{src} pan={pan_f:.1f} tilt={tilt_f:.1f} fps={fps:.1f}",
                    (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
                )

                cv2.imshow("TeruBot Vision (DEBUG)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break

    except Exception as e:
        print("[vision] ERROR:", e)

    finally:
        cap.release()
        if SHOW_DEBUG:
            cv2.destroyAllWindows()
        print("[vision] Tracking stopped")
