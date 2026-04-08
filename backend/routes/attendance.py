from datetime import date
from io import StringIO
import csv
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from core.config import get_settings
from middlewares import get_request_user_id
from schemas.attendance import AttendanceMarkRequest, AttendanceMarkResponse
from services.appwrite_client import appwrite_service
from services.face_recognition import face_service
from services.liveness import detect_head_movement
from utils.geo import haversine_distance_meters
from utils.image import decode_base64_image

router = APIRouter(prefix="/attendance", tags=["attendance"])
settings = get_settings()


@router.post("", response_model=AttendanceMarkResponse)
def mark_attendance(payload: AttendanceMarkRequest, user_id: str = Depends(get_request_user_id)):
    user_role = appwrite_service.get_user_role(user_id)
    if user_role != "student":
        raise HTTPException(status_code=403, detail="Only students can mark attendance.")

    session = appwrite_service.get_session_by_id(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not session.get("is_active"):
        raise HTTPException(status_code=400, detail="Session is not active.")

    session_lat = float(session.get("latitude") or 0.0)
    session_lon = float(session.get("longitude") or 0.0)
    radius_meters = float(session.get("radius_meters") or 0.0)

    distance = haversine_distance_meters(session_lat, session_lon, payload.latitude, payload.longitude)

    if distance > radius_meters:
        marked, record, message = appwrite_service.create_session_attendance(
            user_id=user_id,
            session_id=payload.session_id,
            status="denied",
            distance=distance,
        )
        if marked:
            message = "Attendance denied: outside allowed classroom radius."

        return AttendanceMarkResponse(marked=marked, message=message, record=_to_attendance_record(record, user_id))

    decoded_frames = [decode_base64_image(frame) for frame in payload.frames]
    decoded_frames = [frame for frame in decoded_frames if frame is not None]

    primary_frame = decode_base64_image(payload.frame) if payload.frame else None
    if primary_frame is None and not decoded_frames:
        raise HTTPException(status_code=400, detail="No valid frame provided.")

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
            marked, record, message = appwrite_service.create_session_attendance(
                user_id=user_id,
                session_id=payload.session_id,
                status="denied",
                distance=distance,
            )
            if marked:
                message = f"Attendance denied: {liveness_message}"

            return AttendanceMarkResponse(marked=marked, message=message, record=_to_attendance_record(record, user_id))

    embedding: list[float] | None = None
    if decoded_frames:
        sequence_embeddings = face_service.extract_embeddings(decoded_frames, stride=settings.frame_process_stride)
        embedding = face_service.average_embedding(sequence_embeddings)

    if embedding is None and primary_frame is not None:
        embedding = face_service.extract_embedding_from_frame(primary_frame)

    if embedding is None:
        marked, record, message = appwrite_service.create_session_attendance(
            user_id=user_id,
            session_id=payload.session_id,
            status="denied",
            distance=distance,
        )
        if marked:
            message = "Attendance denied: face not detected."

        return AttendanceMarkResponse(marked=marked, message=message, record=_to_attendance_record(record, user_id))

    users_docs = appwrite_service.get_all_users()
    users = [
        SimpleNamespace(
            id=str(doc.get("user_id") or doc.get("$id") or ""),
            user_code=str(doc.get("user_id") or doc.get("$id") or ""),
            name=doc.get("name") or "Unknown",
            email=doc.get("email") or "",
            embedding=doc.get("embedding") or [],
        )
        for doc in users_docs
    ]

    threshold = payload.threshold if payload.threshold is not None else settings.default_similarity_threshold
    matched, recognized_user, _similarity = face_service.find_best_match(embedding, users, threshold=threshold)

    recognized_user_id = str(recognized_user.id) if recognized_user else ""
    identity_matches_requester = matched and recognized_user_id == user_id

    status_value = "present" if identity_matches_requester else "denied"
    marked, record, message = appwrite_service.create_session_attendance(
        user_id=user_id,
        session_id=payload.session_id,
        status=status_value,
        distance=distance,
    )

    if marked:
        if status_value == "present":
            message = "Attendance marked successfully."
        else:
            message = "Attendance denied: face does not match authenticated student."

    return AttendanceMarkResponse(marked=marked, message=message, record=_to_attendance_record(record, user_id))


def _to_attendance_record(record: dict, user_id: str) -> dict:
    users = appwrite_service.get_all_users()
    user_doc = next((doc for doc in users if str(doc.get("user_id")) == user_id), {})

    return {
        "id": str(record.get("id") or record.get("$id")),
        "user_id": user_id,
        "session_id": str(record.get("session_id") or "") or None,
        "user_name": user_doc.get("name") or "Unknown",
        "user_code": user_id,
        "email": user_doc.get("email") or "",
        "status": record.get("status") or "denied",
        "distance": float(record.get("distance") or 0.0),
        "timestamp": record.get("timestamp") or record.get("$createdAt"),
        "attendance_date": record.get("date") or date.today().isoformat(),
    }


@router.get("")
def get_attendance_logs(
    search: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    export: bool = Query(default=False),
    _user_id: str = Depends(get_request_user_id),
):
    total, items = appwrite_service.get_attendance(
        filters={
            "search": search,
            "session_id": session_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit,
            "offset": offset,
        },
    )

    if export:
        csv_content = _export_csv(items)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance_logs.csv"},
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/export")
def export_attendance_csv(
    search: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _user_id: str = Depends(get_request_user_id),
):
    _, items = appwrite_service.get_attendance(
        filters={
            "search": search,
            "session_id": session_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": 50000,
            "offset": 0,
        }
    )
    csv_content = _export_csv(items)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_logs.csv"},
    )


def _export_csv(items: list[dict]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Attendance ID",
            "Session ID",
            "Class",
            "User ID",
            "User Code",
            "Name",
            "Email",
            "Date",
            "Timestamp",
            "Status",
            "Distance (m)",
        ]
    )

    for item in items:
        writer.writerow(
            [
                item.get("id"),
                item.get("session_id"),
                item.get("class_name"),
                item.get("user_id"),
                item.get("user_code"),
                item.get("user_name"),
                item.get("email"),
                item.get("attendance_date"),
                item.get("timestamp"),
                item.get("status"),
                item.get("distance"),
            ]
        )

    return output.getvalue()
