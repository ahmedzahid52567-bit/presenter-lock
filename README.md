# Presenter Lock

Touch-free presenter control with hand gestures. Open your palm to unlock, and the presenter locks itself again when you stop gesturing — so no one else can take over your slides mid-talk.

## What it does

- **Open palm for 1 second** — unlock
- **Auto-lock after 5 seconds idle** — locks again when you stop
- **Index finger** — laser pointer
- **Swipe right / left** — next / previous slide
- **Pinch / tap micro-gestures** — click / select
- **Circle in the air** — highlight
- **Fist** — lock

Built for the TechKubik 2026 project expo at HKBK, Bengaluru.

## Files

- `presenter_lock.py` — v1, MediaPipe `solutions` API
- `presenter_lock_v2.py` — v2, MediaPipe Tasks API (use this on Python 3.13, where `mp.solutions` was removed)
- `presenter-lock-demo-slides.html` — demo slides to present with it

## Run it

```bash
pip install opencv-python mediapipe pyautogui
python presenter_lock_v2.py
```

For v2 you also need `hand_landmarker.task` in the same folder:
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

Hold your hand about 50 cm from the camera. Press `q` in the camera window to quit.

## Status

Prototype for demo. v2 has not had a successful camera test yet.
