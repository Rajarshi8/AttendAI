from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from deepface import DeepFace

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


@dataclass(frozen=True)
class FaceDetectionResult:
    bbox: tuple[int, int, int, int] | None
    error_code: str | None
    message: str | None
    brightness: float | None = None


class FaceRecognitionService:
    def __init__(self) -> None:
        self.model_name = settings.face_model
        self.default_threshold = settings.default_similarity_threshold
        self.default_stride = max(settings.frame_process_stride, 1)
        self.max_frame_width = max(settings.max_frame_width, 160)

    # ------------------------------------------------------------------
    # Frame preprocessing
    # ------------------------------------------------------------------

    def resize_frame_for_inference(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        if width <= self.max_frame_width:
            return frame
        ratio = self.max_frame_width / float(width)
        resized_height = max(int(height * ratio), 1)
        return cv2.resize(frame, (self.max_frame_width, resized_height), interpolation=cv2.INTER_AREA)

    # ------------------------------------------------------------------
    # Face detection
    # ------------------------------------------------------------------

    def detect_faces(self, gray: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Return a list of (x, y, w, h) bounding boxes for all detected faces."""
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return []
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]

    def analyze_frame(self, frame: np.ndarray) -> tuple[np.ndarray, FaceDetectionResult]:
        resized = self.resize_frame_for_inference(frame)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        if brightness < settings.min_face_brightness:
            return (
                resized,
                FaceDetectionResult(
                    bbox=None,
                    error_code="LOW_LIGHT",
                    message="Lighting is too low. Move to a brighter area.",
                    brightness=brightness,
                ),
            )

        if brightness < settings.low_light_boost_threshold:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

        faces = self.detect_faces(gray)
        if not faces:
            return (
                resized,
                FaceDetectionResult(
                    bbox=None,
                    error_code="FACE_NOT_DETECTED",
                    message="Face not detected. Ensure your face is clearly visible.",
                    brightness=brightness,
                ),
            )

        if len(faces) > 1:
            return (
                resized,
                FaceDetectionResult(
                    bbox=None,
                    error_code="MULTIPLE_FACES",
                    message="Multiple faces detected. Only one person can be in frame.",
                    brightness=brightness,
                ),
            )

        x, y, w, h = faces[0]
        frame_h, frame_w = resized.shape[:2]
        center_x = x + (w / 2)
        center_y = y + (h / 2)
        offset_x = abs(center_x - (frame_w / 2)) / max(frame_w, 1)
        offset_y = abs(center_y - (frame_h / 2)) / max(frame_h, 1)

        if max(offset_x, offset_y) > settings.max_face_center_offset_ratio:
            return (
                resized,
                FaceDetectionResult(
                    bbox=None,
                    error_code="FACE_NOT_CENTERED",
                    message="Center your face in the frame and try again.",
                    brightness=brightness,
                ),
            )

        return (
            resized,
            FaceDetectionResult(bbox=(x, y, w, h), error_code=None, message=None, brightness=brightness),
        )

    # ------------------------------------------------------------------
    # Embedding extraction
    # ------------------------------------------------------------------

    def extract_embedding_from_frame(self, frame: np.ndarray) -> list[float] | None:
        embedding, _reason = self.extract_embedding_with_reason(frame)
        return embedding

    def extract_embedding_with_reason(
        self, frame: np.ndarray
    ) -> tuple[list[float] | None, FaceDetectionResult | None]:
        resized, detection = self.analyze_frame(frame)
        if detection.error_code:
            return None, detection
        x, y, w, h = detection.bbox or (0, 0, 0, 0)
        face_crop = resized[y : y + h, x : x + w]
        if face_crop.size == 0:
            return None, FaceDetectionResult(None, "FACE_NOT_DETECTED", "Face crop failed.")

        face_crop = cv2.resize(face_crop, (160, 160))

        try:
            result = DeepFace.represent(
                img_path=face_crop,
                model_name=self.model_name,
                detector_backend="opencv",
                enforce_detection=False,
            )
            if not result:
                return None, FaceDetectionResult(None, "FACE_NOT_DETECTED", "Face not detected.")
            embedding = result[0].get("embedding")
            if not embedding:
                return None, FaceDetectionResult(None, "FACE_NOT_DETECTED", "Face not detected.")
            return [float(v) for v in embedding], None
        except Exception as exc:
            logger.debug("DeepFace.represent failed: %s", exc)
            return None, FaceDetectionResult(None, "FACE_NOT_DETECTED", "Face embedding failed.")

    def extract_embeddings(self, frames: Sequence[np.ndarray], stride: int | None = None) -> list[list[float]]:
        process_stride = max(stride or self.default_stride, 1)
        embeddings: list[list[float]] = []

        for idx, frame in enumerate(frames):
            if idx % process_stride != 0:
                continue
            embedding, _reason = self.extract_embedding_with_reason(frame)
            if embedding is not None:
                embeddings.append(embedding)

        return embeddings

    # ------------------------------------------------------------------
    # Embedding math
    # ------------------------------------------------------------------

    @staticmethod
    def average_embedding(embeddings: Sequence[Sequence[float]]) -> list[float] | None:
        if not embeddings:
            return None
        arr = np.array(embeddings, dtype=np.float32)
        avg = np.mean(arr, axis=0)
        return avg.tolist()

    @staticmethod
    def cosine_similarity(embedding_a: Sequence[float], embedding_b: Sequence[float]) -> float:
        a = np.array(embedding_a, dtype=np.float32)
        b = np.array(embedding_b, dtype=np.float32)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def find_best_match(
        self,
        embedding: Sequence[float],
        users: Sequence,
        threshold: float | None = None,
    ) -> tuple[bool, object | None, float]:
        """
        Find the best embedding match from a list of user objects.

        Each user must have: .id, .embedding (list[float]).

        Returns: (matched: bool, best_user | None, best_similarity: float)
        """
        similarity_threshold = threshold if threshold is not None else self.default_threshold
        best_user = None
        best_similarity = -1.0

        for user in users:
            stored_embedding = user.embedding
            if not stored_embedding:
                continue
            similarity = self.cosine_similarity(embedding, stored_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_user = user

        matched = best_user is not None and best_similarity >= similarity_threshold

        if best_user is not None:
            logger.debug(
                "Best match: user=%s similarity=%.4f threshold=%.2f matched=%s",
                getattr(best_user, "id", "?"),
                best_similarity,
                similarity_threshold,
                matched,
            )

        return matched, best_user, float(max(best_similarity, 0.0))


face_service = FaceRecognitionService()
