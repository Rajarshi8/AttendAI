import base64
from typing import Optional, Tuple

import cv2
import numpy as np

from core.config import get_settings

settings = get_settings()


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


def decode_base64_image_checked(image_base64: str) -> Tuple[Optional[np.ndarray], Optional[str], Optional[str]]:
    """Decode and validate base64 image payloads.

    Returns: (frame, error_code, message)
    """
    if not image_base64:
        return None, "INVALID_IMAGE", "No image data provided."

    mime_type = None
    if image_base64.startswith("data:") and "," in image_base64:
        header, image_base64 = image_base64.split(",", 1)
        mime_type = header.split(";", 1)[0].replace("data:", "").strip().lower()

    if mime_type and mime_type not in {t.lower() for t in settings.allowed_image_mime_types}:
        return None, "UNSUPPORTED_MEDIA_TYPE", "Unsupported image type. Use JPEG or PNG."

    approx_bytes = (len(image_base64) * 3) // 4
    if approx_bytes > settings.max_image_bytes:
        return None, "IMAGE_TOO_LARGE", "Image payload too large."

    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
        if len(image_bytes) > settings.max_image_bytes:
            return None, "IMAGE_TOO_LARGE", "Image payload too large."

        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None, "INVALID_IMAGE", "Invalid image payload."

        height, width = frame.shape[:2]
        if width > settings.max_image_width or height > settings.max_image_height:
            return None, "IMAGE_TOO_LARGE", "Image dimensions exceed maximum allowed size."

        return frame, None, None
    except Exception:
        return None, "INVALID_IMAGE", "Invalid image payload."


def image_error_status_code(error_code: str | None) -> int:
    if error_code == "IMAGE_TOO_LARGE":
        return 413
    if error_code == "UNSUPPORTED_MEDIA_TYPE":
        return 415
    return 400
