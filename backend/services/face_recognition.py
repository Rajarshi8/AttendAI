from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np
from deepface import DeepFace

from core.config import get_settings

settings = get_settings()

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


class FaceRecognitionService:
    def __init__(self) -> None:
        self.model_name = settings.face_model
        self.default_threshold = settings.default_similarity_threshold
        self.default_stride = max(settings.frame_process_stride, 1)
        self.max_frame_width = max(settings.max_frame_width, 160)

    def resize_frame_for_inference(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        if width <= self.max_frame_width:
            return frame
        ratio = self.max_frame_width / float(width)
        resized_height = max(int(height * ratio), 1)
        return cv2.resize(frame, (self.max_frame_width, resized_height), interpolation=cv2.INTER_AREA)

    def detect_face_bbox(self, frame: np.ndarray) -> tuple[int, int, int, int] | None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None

        faces = sorted(faces, key=lambda rect: rect[2] * rect[3], reverse=True)
        x, y, w, h = faces[0]
        return int(x), int(y), int(w), int(h)

    def extract_embedding_from_frame(self, frame: np.ndarray) -> list[float] | None:
        frame = self.resize_frame_for_inference(frame)
        bbox = self.detect_face_bbox(frame)
        if bbox is None:
            return None

        x, y, w, h = bbox
        face_crop = frame[y : y + h, x : x + w]
        if face_crop.size == 0:
            return None

        face_crop = cv2.resize(face_crop, (160, 160))

        try:
            result = DeepFace.represent(
                img_path=face_crop,
                model_name=self.model_name,
                detector_backend="opencv",
                enforce_detection=False,
            )
            if not result:
                return None
            embedding = result[0].get("embedding")
            if not embedding:
                return None
            return [float(x) for x in embedding]
        except Exception:
            return None

    def extract_embeddings(self, frames: Sequence[np.ndarray], stride: int | None = None) -> list[list[float]]:
        process_stride = max(stride or self.default_stride, 1)
        embeddings: list[list[float]] = []

        for idx, frame in enumerate(frames):
            if idx % process_stride != 0:
                continue
            embedding = self.extract_embedding_from_frame(frame)
            if embedding is not None:
                embeddings.append(embedding)

        return embeddings

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

    def find_best_match(self, embedding: Sequence[float], users: Sequence, threshold: float | None = None):
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
        return matched, best_user, float(best_similarity if best_similarity >= 0 else 0.0)


face_service = FaceRecognitionService()
