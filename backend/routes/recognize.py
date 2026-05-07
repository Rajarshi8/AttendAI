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
from utils.image import decode_base64_image_checked, image_error_status_code

settings = get_settings()
router = APIRouter(prefix="/recognize", tags=["recognition"])
logger = get_logger(__name__)

DETECTION_MESSAGES = {
    "MULTIPLE_FACES": "Multiple faces detected. Only one person can be in frame.",
    "LOW_LIGHT": "Lighting is too low. Move to a brighter area.",
    "FACE_NOT_CENTERED": "Center your face in the frame and try again.",
}


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
    decoded_frames: list = []
    for frame in payload.frames:
        decoded, error_code, message = decode_base64_image_checked(frame)
        if error_code:
            raise HTTPException(status_code=image_error_status_code(error_code), detail=message)
        if decoded is not None:
            decoded_frames.append(decoded)

    primary_frame = None
    if payload.frame:
        decoded, error_code, message = decode_base64_image_checked(payload.frame)
        if error_code:
            raise HTTPException(status_code=image_error_status_code(error_code), detail=message)
        primary_frame = decoded
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
            log_recognition(
                logger,
                user_id="unknown",
                similarity=None,
                matched=False,
                status="liveness_failed",
                request_id=getattr(request.state, "request_id", None),
                error_code="LIVENESS_FAILED",
            )
            return RecognizeResponse(
                matched=False,
                live=False,
                similarity=None,
                user=None,
                message=liveness_message,
                error_code="LIVENESS_FAILED",
            )
    else:
        live = True

    # ── Embedding extraction ─────────────────────────────────────────────────
    embedding: list[float] | None = None
    reason_code: str | None = None

    if decoded_frames:
        embeddings: list[list[float]] = []
        for idx, frame in enumerate(decoded_frames):
            if idx % max(settings.frame_process_stride, 1) != 0:
                continue
            emb, reason = face_service.extract_embedding_with_reason(frame)
            if emb is not None:
                embeddings.append(emb)
            elif reason and not reason_code:
                reason_code = reason.error_code
        embedding = face_service.average_embedding(embeddings)

    if embedding is None and primary_frame is not None:
        emb, reason = face_service.extract_embedding_with_reason(primary_frame)
        embedding = emb
        if reason and not reason_code:
            reason_code = reason.error_code

    if embedding is None:
        error_code = reason_code or "FACE_NOT_DETECTED"
        log_recognition(
            logger,
            user_id="unknown",
            similarity=None,
            matched=False,
            status="face_rejected",
            request_id=getattr(request.state, "request_id", None),
            error_code=error_code,
        )
        return RecognizeResponse(
            matched=False,
            live=live,
            similarity=None,
            user=None,
            message=DETECTION_MESSAGES.get(
                error_code,
                "Face not detected or embedding extraction failed.",
            ),
            error_code=error_code,
        )

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
        request_id=getattr(request.state, "request_id", None),
        error_code=None if matched else "FACE_MISMATCH",
    )

    if not matched or user is None:
        return RecognizeResponse(
            matched=False,
            live=live,
            similarity=similarity,
            user=None,
            message="Face not recognized. Ensure you are registered and well-lit.",
            error_code="FACE_MISMATCH",
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
        error_code=None,
    )
