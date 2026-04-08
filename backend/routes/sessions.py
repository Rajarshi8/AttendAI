from fastapi import APIRouter, Depends, HTTPException, Query

from middlewares import get_request_user_id
from schemas.session import (
    ActiveSessionResponse,
    SessionItem,
    SessionStartRequest,
    SessionStartResponse,
    SessionStopRequest,
    SessionStopResponse,
)
from services.appwrite_client import appwrite_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _as_session_item(document: dict) -> SessionItem:
    return SessionItem(
        session_id=str(document.get("session_id") or document.get("$id") or ""),
        admin_id=str(document.get("admin_id") or ""),
        class_name=str(document.get("class_name") or ""),
        start_time=document.get("start_time") or document.get("$createdAt"),
        end_time=document.get("end_time"),
        latitude=float(document.get("latitude") or 0.0),
        longitude=float(document.get("longitude") or 0.0),
        radius_meters=float(document.get("radius_meters") or 0.0),
        is_active=bool(document.get("is_active")),
    )


def _require_admin(user_id: str) -> None:
    role = appwrite_service.get_user_role(user_id)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required.")


@router.post("/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest, user_id: str = Depends(get_request_user_id)):
    _require_admin(user_id)

    session_doc = appwrite_service.create_session(
        admin_id=user_id,
        class_name=payload.class_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        end_time=payload.end_time.isoformat() if payload.end_time else None,
    )

    return SessionStartResponse(message="Attendance session started.", session=_as_session_item(session_doc))


@router.post("/stop", response_model=SessionStopResponse)
def stop_session(payload: SessionStopRequest, user_id: str = Depends(get_request_user_id)):
    _require_admin(user_id)

    existing = appwrite_service.get_session_by_id(payload.session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found.")

    owner_id = str(existing.get("admin_id") or "")
    if owner_id and owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the creator admin can stop this session.")

    updated = appwrite_service.stop_session(payload.session_id)
    return SessionStopResponse(message="Attendance session stopped.", session=_as_session_item(updated))


@router.get("/active", response_model=ActiveSessionResponse)
def get_active_session(_user_id: str = Depends(get_request_user_id)):
    active_session = appwrite_service.get_active_session()
    if not active_session:
        return ActiveSessionResponse(session=None)
    return ActiveSessionResponse(session=_as_session_item(active_session))


@router.get("", response_model=list[SessionItem])
def list_sessions(
    mine: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_request_user_id),
):
    _require_admin(user_id)

    sessions = appwrite_service.list_sessions(admin_id=user_id if mine else None, limit=limit)
    return [_as_session_item(doc) for doc in sessions]
