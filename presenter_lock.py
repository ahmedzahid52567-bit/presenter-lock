# Presenter Lock - TechKubik 2026
# Hand-gesture presenter that fixes gaps in old gesture demos:
#  1. Presenter Lock: show OPEN PALM for 1 second to unlock.
#     Talking hands are ignored when locked. Auto-locks after 5 sec idle.
#  2. First-hand lock: only the FIRST hand controls. A second hand is ignored,
#     so an audience member cannot hijack your slides.
#  3. Finger Pointer: index finger only = red laser pointer (moves your mouse).
#  4. Swipe: while unlocked, move your open hand right = next slide,
#     left = previous slide. Fist = lock immediately.
#
# HOW TO RUN (on your laptop, with a webcam):
#   pip install opencv-python mediapipe pyautogui
#   python presenter_lock.py
#   - Keep your hand about 50 cm from the camera, in good light.
#   - Open your slides in fullscreen FIRST (PowerPoint / PDF viewer),
#     then run this, then click back on the slides window.
#     Actually, simplest for tomorrow: run this in a small window beside
#     your slides, and let the judges watch the camera window.
#   - Press 'q' to quit.
# SAFETY: pyautogui moves your real mouse in Pointer mode and presses
# Right/Left arrows for slides. Move your mouse to a corner to stop it
# (pyautogui failsafe), or press 'q' in the camera window.

import time
import cv2
import mediapipe as mp

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    SCREEN_W, SCREEN_H = pyautogui.size()
    HAVE_GUI = True
except Exception as e:
    print("pyautogui not available, pointer/slide control off:", e)
    SCREEN_W, SCREEN_H = 1920, 1080
    HAVE_GUI = False

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Finger tip / pip landmark ids: index, middle, ring, pinky
FINGERS = [(8, 6), (12, 10), (16, 14), (20, 18)]


def fingers_up(landmarks):
    """Return a list of True/False for index, middle, ring, pinky.
    A finger is 'up' when its tip is above (smaller y than) its pip joint.
    Works for a hand held upright in front of the camera."""
    out = []
    for tip, pip in FINGERS:
        out.append(landmarks[tip].y < landmarks[pip].y)
    return out


def main():
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

    with mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    ) as hands:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            status = "LOCKED" if not unlocked else "UNLOCKED"
            status_color = (0, 0, 255) if not unlocked else (0, 200, 0)
            gesture = "No hand"
            second_hand = False

            if result.multi_hand_landmarks:
                # GAP FIX 2: only the FIRST hand controls. Others are ignored.
                if len(result.multi_hand_landmarks) > 1:
                    second_hand = True
                lm = result.multi_hand_landmarks[0].landmark
                mp_draw.draw_landmarks(frame, result.multi_hand_landmarks[0],
                                       mp_hands.HAND_CONNECTIONS)
                up = fingers_up(lm)
                n_up = sum(up)
                wrist_x = lm[0].x
                now = time.time()

                # Fist = lock immediately (all 4 fingers down)
                if n_up == 0:
                    if unlocked:
                        unlocked = False
                        flash_text, flash_until = "LOCKED", now + 1.0
                    gesture = "Fist = Lock"
                    palm_start = None
                    swipe_start_x = None

                # Open palm = all 4 fingers up
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
                        # Swipe: track wrist movement while palm is open
                        if swipe_start_x is None:
                            swipe_start_x, swipe_start_t = wrist_x, now
                        elif now - swipe_start_t > 0.15:
                            dx = wrist_x - swipe_start_x
                            if now - last_action > 1.0:  # 1 sec cooldown
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

                # Index finger only = pointer
                elif up == [True, False, False, False]:
                    gesture = "Pointer"
                    if unlocked:
                        last_activity = now
                        ix, iy = int(lm[8].x * w), int(lm[8].y * h)
                        cv2.circle(frame, (ix, iy), 12, (0, 0, 255), -1)
                        if HAVE_GUI:
                            try:
                                pyautogui.moveTo(int(lm[8].x * SCREEN_W),
                                                 int(lm[8].y * SCREEN_H),
                                                 duration=0.05)
                            except Exception:
                                pass
                    palm_start = None
                    swipe_start_x = None

                else:
                    gesture = "Hand seen - show palm / index / fist"
                    palm_start = None
                    swipe_start_x = None

                # GAP FIX 1: auto-lock after 5 seconds with no unlocked action
                if unlocked and time.time() - last_activity > 5.0:
                    unlocked = False
                    flash_text = "AUTO-LOCKED"
                    flash_until = time.time() + 1.0
            else:
                palm_start = None
                swipe_start_x = None

            # On-screen status (this is the feedback old demos miss)
            cv2.putText(frame, f"Presenter Lock: {status}", (10, 30),
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

            cv2.imshow("Presenter Lock - TechKubik", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
