from collections.abc import Sequence

import cv2
import numpy as np

from core.config import get_settings

settings = get_settings()
MAX_FRAME_WIDTH = max(settings.max_frame_width, 160)

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def _face_center(frame: np.ndarray) -> tuple[float, float] | None:
    height, width = frame.shape[:2]
    if width > MAX_FRAME_WIDTH:
        ratio = MAX_FRAME_WIDTH / float(width)
        resized_height = max(int(height * ratio), 1)
        frame = cv2.resize(frame, (MAX_FRAME_WIDTH, resized_height), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None

    faces = sorted(faces, key=lambda rect: rect[2] * rect[3], reverse=True)
    x, y, w, h = faces[0]
    return float(x + (w / 2)), float(y + (h / 2))


def detect_head_movement(
    frames: Sequence[np.ndarray],
    min_frames: int | None = None,
    min_displacement: float | None = None,
) -> tuple[bool, str]:
    required_frames = min_frames if min_frames is not None else settings.liveness_min_frames
    displacement_threshold = min_displacement if min_displacement is not None else settings.liveness_min_displacement

    centers: list[tuple[float, float]] = []
    for frame in frames:
        center = _face_center(frame)
        if center is not None:
            centers.append(center)

    if len(centers) < required_frames:
        return False, "Not enough valid face frames for liveness check."

    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]

    x_disp = max(xs) - min(xs)
    y_disp = max(ys) - min(ys)

    if x_disp >= displacement_threshold or y_disp >= (displacement_threshold * 0.7):
        return True, "Liveness check passed."

    return False, "Liveness check failed. Please move your head slightly."
