import base64
from typing import Optional

import cv2
import numpy as np


def decode_base64_image(image_base64: str) -> Optional[np.ndarray]:
    if not image_base64:
        return None

    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_base64)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except Exception:
        return None
