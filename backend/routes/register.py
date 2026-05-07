from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.logging import get_logger
from middlewares import get_request_user
from schemas.user import RegisterRequest, UserResponse
from services.appwrite_client import appwrite_service
from services.cache import embedding_cache
from services.face_recognition import face_service
from utils.image import decode_base64_image

router = APIRouter(prefix="/register", tags=["registration"])
logger = get_logger(__name__)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, auth_user: dict = Depends(get_request_user)) -> UserResponse:
    """
    Register face embeddings for the authenticated user.
    Requires 10–20 clear face images.
    Invalidates the embedding cache on success so the new embedding is available immediately.
    """
    user_id = str(auth_user.get("$id", ""))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity from token.")

    email = auth_user.get("email") or ""
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated account is missing email.")

    name = auth_user.get("name") or email or "User"

    decoded_frames = [decode_base64_image(image) for image in payload.images]
    decoded_frames = [frame for frame in decoded_frames if frame is not None]

    if len(decoded_frames) < 10:
        raise HTTPException(status_code=400, detail="At least 10 valid face images are required.")

    embeddings = face_service.extract_embeddings(decoded_frames, stride=1)
    if len(embeddings) < 8:
        raise HTTPException(
            status_code=400,
            detail="Could not extract enough face embeddings. Ensure your face is clearly visible and well-lit.",
        )

    average_embedding = face_service.average_embedding(embeddings)
    if average_embedding is None:
        raise HTTPException(status_code=400, detail="Failed to create face embedding. Please try again.")

    user_doc = appwrite_service.ensure_user_doc_from_account(auth_user)
    appwrite_service.store_embedding(user_id=user_id, embedding=average_embedding)

    # Invalidate cache so this user's embedding is available on the next request
    embedding_cache.invalidate()
    logger.info("User %s registered face — embedding cache invalidated.", user_id)

    return UserResponse(
        id=user_id,
        name=name,
        email=email,
        user_id=user_id,
        role=appwrite_service.get_user_role(user_id),
        face_samples=len(embeddings),
    )
