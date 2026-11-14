# Presenter Lock v2 - TechKubik 2026
# FIX for: AttributeError: module 'mediapipe' has no attribute 'solutions'
# On Python 3.13, the new mediapipe removed mp.solutions.
# This version uses the NEW MediaPipe Tasks API instead, so it works
# with the mediapipe you already installed. Same gestures as before:
#  Palm 1 sec = Unlock | Auto-lock after 5 sec idle | First hand only
#  Swipe right/left = Next/Prev slide | Index finger = Pointer | Fist = Lock
#
# YOU NEED ONE EXTRA FILE, IN THE SAME FOLDER AS THIS CODE:
#   hand_landmarker.task
# Download it from (click / copy this link):
#   https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
# Save it in Downloads, next to presenter_lock_v2.py. Do NOT rename it.
#
# HOW TO RUN (you are already in Downloads in Command Prompt):
#   python presenter_lock_v2.py
# Do NOT run "cd Downloads" again if you are already in Downloads -
# that gives "The system cannot find the path specified" because
# Downloads inside Downloads does not exist.
# Press 'q' in the camera window to quit. Hand about 50 cm from camera.

import os
import time
import cv2

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    SCREEN_W, SCREEN_H = pyautogui.size()
    HAVE_GUI = True
except Exception as e:
    print("pyautogui not available, pointer/slide control off:", e)
    SCREEN_W, SCREEN_H = 1920, 1080
    HAVE_GUI = False

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Hand connections for drawing (21 landmarks)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

FINGERS = [(8, 6), (12, 10), (16, 14), (20, 18)]


def fingers_up(landmarks):
    out = []
    for tip, pip in FINGERS:
        out.append(landmarks[tip].y < landmarks[pip].y)
    return out


def find_model():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    for path in [os.path.join(here, "hand_landmarker.task"),
                 "hand_landmarker.task"]:
        if os.path.exists(path):
            return path
    return None


def main():
    model_path = find_model()
    if model_path is None:
        print("ERROR: hand_landmarker.task NOT FOUND in this folder.")
        print("Download it from:")
        print("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
        print("Save it in the SAME folder as presenter_lock_v2.py, then run again.")
        return

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: webcam not found. Close other apps using the camera and try again.")
        return

    unlocked = False
    palm_start = None
    last_action = 0.0
    last_activity = time.time()
    swipe_start_x = None
    swipe_start_t = 0.0
    flash_until = 0.0
    flash_text = ""
    frame_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_count += 1
        timestamp_ms = frame_count * 33
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        status = "LOCKED" if not unlocked else "UNLOCKED"
        status_color = (0, 0, 255) if not unlocked else (0, 200, 0)
        gesture = "No hand"
        second_hand = False
        hands_list = result.hand_landmarks or []

        if hands_list:
            if len(hands_list) > 1:
                second_hand = True
            lm = hands_list[0]
            # Draw hand skeleton manually (Tasks API has no drawing_utils)
            for a, b in HAND_CONNECTIONS:
                x1, y1 = int(lm[a].x * w), int(lm[a].y * h)
                x2, y2 = int(lm[b].x * w), int(lm[b].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            for pt in lm:
                cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 3, (0, 255, 0), -1)

            up = fingers_up(lm)
            n_up = sum(up)
            wrist_x = lm[0].x
            now = time.time()

            if n_up == 0:
                if unlocked:
                    unlocked = False
                    flash_text, flash_until = "LOCKED", now + 1.0
                gesture = "Fist = Lock"
                palm_start = None
                swipe_start_x = None
            elif n_up == 4:
                gesture = "Open palm"
                if not unlocked:
                    if palm_start is None:
                        palm_start = now
                    held = now - palm_start
                    gesture = f"Open palm held {held:.1f}s - hold 1s to unlock"
                    if held >= 1.0:
                        unlocked = True
                        last_activity = now
                        flash_text, flash_until = "UNLOCKED", now + 1.0
                        palm_start = None
                        swipe_start_x = None
                else:
                    last_activity = now
                    if swipe_start_x is None:
                        swipe_start_x, swipe_start_t = wrist_x, now
                    elif now - swipe_start_t > 0.15:
                        dx = wrist_x - swipe_start_x
                        if now - last_action > 1.0:
                            if dx > 0.15:
                                gesture = "Swipe RIGHT = Next slide"
                                if HAVE_GUI:
                                    pyautogui.press("right")
                                last_action = now
                                flash_text, flash_until = "NEXT SLIDE", now + 1.0
                                swipe_start_x = None
                            elif dx < -0.15:
                                gesture = "Swipe LEFT = Previous slide"
                                if HAVE_GUI:
                                    pyautogui.press("left")
                                last_action = now
                                flash_text, flash_until = "PREV SLIDE", now + 1.0
                                swipe_start_x = None
                        if now - swipe_start_t > 1.0:
                            swipe_start_x = None
            elif up == [True, False, False, False]:
                gesture = "Pointer"
                if unlocked:
                    last_activity = now
                    ix, iy = int(lm[8].x * w), int(lm[8].y * h)
                    cv2.circle(frame, (ix, iy), 12, (0, 0, 255), -1)
                    if HAVE_GUI:
                        try:
                            pyautogui.moveTo(int(lm[8].x * SCREEN_W),
                                             int(lm[8].y * SCREEN_H), duration=0.05)
                        except Exception:
                            pass
                palm_start = None
                swipe_start_x = None
            else:
                gesture = "Hand seen - show palm / index / fist"
                palm_start = None
                swipe_start_x = None

            if unlocked and time.time() - last_activity > 5.0:
                unlocked = False
                flash_text = "AUTO-LOCKED"
                flash_until = time.time() + 1.0
        else:
            palm_start = None
            swipe_start_x = None

        cv2.putText(frame, f"Presenter Lock v2: {status}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        cv2.putText(frame, gesture, (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if second_hand:
            cv2.putText(frame, "2nd hand IGNORED (first-hand lock)", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        if time.time() < flash_until:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 200, 0), 8)
            cv2.putText(frame, flash_text, (10, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 0), 3)
        cv2.putText(frame, "Palm 1s=Unlock | Swipe=Slides | Index=Pointer | Fist=Lock | q=Quit",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        cv2.imshow("Presenter Lock v2 - TechKubik", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
