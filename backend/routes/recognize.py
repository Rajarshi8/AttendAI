from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import get_settings
from core.logging import get_logger, log_recognition
from middlewares import get_request_user
from schemas.recognition import RecognizeRequest, RecognizeResponse
from services.cache import embedding_cache
from services.face_recognition import face_service
from services.liveness import detect_head_movement
from services.rate_limiter import limiter
from utils.image import decode_base64_image

settings = get_settings()
router = APIRouter(prefix="/recognize", tags=["recognition"])
logger = get_logger(__name__)


@router.post("", response_model=RecognizeResponse)
@limiter.limit("20/minute")
def recognize_user(
    request: Request,
    payload: RecognizeRequest,
    _auth_user: dict = Depends(get_request_user),
) -> RecognizeResponse:
    """
    Identify a face against the cached embedding store.
    Rate-limited to 20 requests/minute per IP.
    """
    decoded_frames = [decode_base64_image(frame) for frame in payload.frames]
    decoded_frames = [frame for frame in decoded_frames if frame is not None]

    primary_frame = decode_base64_image(payload.frame) if payload.frame else None
    if primary_frame is None and not decoded_frames:
        raise HTTPException(status_code=400, detail="No valid frame provided.")

    # ── Liveness check ───────────────────────────────────────────────────────
    if payload.require_liveness:
        frames_for_liveness = decoded_frames.copy()
        if primary_frame is not None:
            frames_for_liveness.append(primary_frame)

        live, liveness_message = detect_head_movement(
            frames_for_liveness,
            min_frames=settings.liveness_min_frames,
            min_displacement=settings.liveness_min_displacement,
        )
        if not live:
            logger.info("Liveness failed during recognition: %s", liveness_message)
            return RecognizeResponse(
                matched=False,
                live=False,
                similarity=None,
                user=None,
                message=liveness_message,
            )
    else:
        live = True

    # ── Embedding extraction ─────────────────────────────────────────────────
    embedding: list[float] | None = None
    if decoded_frames:
        sequence_embeddings = face_service.extract_embeddings(decoded_frames, stride=settings.frame_process_stride)
        embedding = face_service.average_embedding(sequence_embeddings)

    if embedding is None and primary_frame is not None:
        embedding = face_service.extract_embedding_from_frame(primary_frame)

    if embedding is None:
        raise HTTPException(status_code=400, detail="Face not detected or embedding extraction failed.")

    # ── Match against cache ──────────────────────────────────────────────────
    embedding_cache.refresh_if_stale()
    users = embedding_cache.get_all()

    threshold = payload.threshold if payload.threshold is not None else settings.default_similarity_threshold
    matched, user, similarity = face_service.find_best_match(embedding, users, threshold=threshold)

    # ── Log result ───────────────────────────────────────────────────────────
    log_recognition(
        logger,
        user_id=user.id if user else "unknown",
        similarity=similarity,
        matched=matched,
        status="matched" if matched else "no_match",
    )

    if not matched or user is None:
        return RecognizeResponse(
            matched=False,
            live=live,
            similarity=similarity,
            user=None,
            message="Face not recognized. Ensure you are registered and well-lit.",
        )

    return RecognizeResponse(
        matched=True,
        live=live,
        similarity=similarity,
        user={
            "id": user.id,
            "user_id": user.user_code,
            "name": user.name,
            "email": user.email,
        },
        message="User recognized successfully.",
    )
