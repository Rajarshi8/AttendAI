from fastapi import APIRouter, Depends, HTTPException

from middlewares import get_request_user
from schemas.user import CurrentUserResponse
from services.appwrite_client import appwrite_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
def get_me(auth_user: dict = Depends(get_request_user)):
    user_id = str(auth_user.get("$id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity from token.")

    email = str(auth_user.get("email") or "")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated account is missing email.")

    name = str(auth_user.get("name") or email or "User")
    user_doc = appwrite_service.ensure_user_doc(user_id=user_id, name=name, email=email, role="student")

    embedding = user_doc.get("embedding") or []

    return CurrentUserResponse(
        user_id=user_id,
        name=user_doc.get("name") or name,
        email=user_doc.get("email") or email,
        role=appwrite_service.get_user_role(user_id),
        has_embedding=bool(embedding),
    )
