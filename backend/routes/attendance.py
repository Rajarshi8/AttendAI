from __future__ import annotations

import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from core.config import get_settings
from core.logging import get_logger, log_recognition
from middlewares import get_request_user_id
from schemas.attendance import AttendanceMarkRequest, AttendanceMarkResponse
from services.appwrite_client import appwrite_service
from services.cache import embedding_cache
from services.face_recognition import face_service
from services.liveness import detect_head_movement
from services.rate_limiter import limiter
from utils.geo import haversine_distance_meters
from utils.image import decode_base64_image

router = APIRouter(prefix="/attendance", tags=["attendance"])
settings = get_settings()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# POST /attendance — Mark attendance
# ---------------------------------------------------------------------------

@router.post("", response_model=AttendanceMarkResponse)
@limiter.limit("10/minute")
def mark_attendance(
    request: Request,
    payload: AttendanceMarkRequest,
    user_id: str = Depends(get_request_user_id),
) -> AttendanceMarkResponse:
    """
    Mark student attendance for an active session.
    Validates: role, session active, GPS accuracy, geofence, liveness, face match.
    user_id is ALWAYS taken from the JWT — never from the request body.
    """

    # ── RBAC ────────────────────────────────────────────────────────────────
    user_role = appwrite_service.get_user_role(user_id)
    if user_role != "student":
        raise HTTPException(status_code=403, detail="Only students can mark attendance.")

    # ── Session validation ───────────────────────────────────────────────────
    session = appwrite_service.get_session_by_id(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not session.get("is_active"):
        raise HTTPException(status_code=400, detail="Session is not active.")

    # ── GPS accuracy check ───────────────────────────────────────────────────
    if payload.gps_accuracy is not None and payload.gps_accuracy > settings.gps_accuracy_limit_meters:
        logger.warning(
            "GPS accuracy too low for user %s (%.1f m > %.1f m limit)",
            user_id,
            payload.gps_accuracy,
            settings.gps_accuracy_limit_meters,
        )
        return AttendanceMarkResponse(
            marked=False,
            message=f"GPS signal is too weak (accuracy: {payload.gps_accuracy:.0f}m). Move to a location with better GPS signal.",
            error_code="LOW_GPS_ACCURACY",
        )

    # ── Geofence check (with buffer) ─────────────────────────────────────────
    session_lat = float(session.get("latitude") or 0.0)
    session_lon = float(session.get("longitude") or 0.0)
    radius_meters = float(session.get("radius_meters") or 0.0)
    effective_radius = radius_meters + settings.geofence_buffer_meters

    distance = haversine_distance_meters(session_lat, session_lon, payload.latitude, payload.longitude)

    if distance > effective_radius:
        logger.info(
            "Geofence denial for user %s: %.1f m from session center (limit %.1f m)",
            user_id,
            distance,
            effective_radius,
        )
        marked, record, message = appwrite_service.create_session_attendance(
            user_id=user_id,
            session_id=payload.session_id,
            status="denied",
            distance=distance,
        )
        error_msg = f"You are {distance:.0f}m from the classroom (limit: {effective_radius:.0f}m)."
        return AttendanceMarkResponse(
            marked=marked,
            message=error_msg if marked else message,
            error_code="OUT_OF_RANGE",
            record=_to_attendance_record(record, user_id) if marked else None,
        )

    # ── Decode frames ────────────────────────────────────────────────────────
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
            marked, record, message = appwrite_service.create_session_attendance(
                user_id=user_id,
                session_id=payload.session_id,
                status="denied",
                distance=distance,
            )
            return AttendanceMarkResponse(
                marked=marked,
                message=f"Liveness check failed: {liveness_message}" if marked else message,
                error_code="LIVENESS_FAILED",
                record=_to_attendance_record(record, user_id) if marked else None,
            )

    # ── Embedding extraction ─────────────────────────────────────────────────
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
        return AttendanceMarkResponse(
            marked=marked,
            message="Face not detected. Ensure your face is clearly visible and well-lit." if marked else message,
            error_code="FACE_NOT_DETECTED",
            record=_to_attendance_record(record, user_id) if marked else None,
        )

    # ── Face matching (from cache) ────────────────────────────────────────────
    embedding_cache.refresh_if_stale()
    users = embedding_cache.get_all()

    threshold = payload.threshold if payload.threshold is not None else settings.default_similarity_threshold
    matched, recognized_user, similarity = face_service.find_best_match(embedding, users, threshold=threshold)

    recognized_user_id = str(recognized_user.id) if recognized_user else ""
    identity_matches_requester = matched and recognized_user_id == user_id

    status_value = "present" if identity_matches_requester else "denied"

    # ── Log recognition result ────────────────────────────────────────────────
    log_recognition(
        logger,
        user_id=user_id,
        session_id=payload.session_id,
        similarity=similarity,
        distance=distance,
        matched=identity_matches_requester,
        status=status_value,
    )

    # ── Record attendance ─────────────────────────────────────────────────────
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
            message = "Face does not match your registered profile."

    error_code = None if status_value == "present" else "FACE_MISMATCH"

    return AttendanceMarkResponse(
        marked=marked,
        message=message,
        error_code=error_code if status_value == "denied" else None,
        record=_to_attendance_record(record, user_id),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_attendance_record(record: dict, user_id: str) -> dict:
    """Build the attendance record response from cached user data — no extra Appwrite call."""
    users = embedding_cache.get_all()
    user_ns = next((u for u in users if u.id == user_id), None)

    return {
        "id": str(record.get("id") or record.get("$id")),
        "user_id": user_id,
        "session_id": str(record.get("session_id") or "") or None,
        "user_name": user_ns.name if user_ns else "Unknown",
        "user_code": user_id,
        "email": user_ns.email if user_ns else "",
        "status": record.get("status") or "denied",
        "distance": float(record.get("distance") or 0.0),
        "timestamp": record.get("timestamp") or record.get("$createdAt"),
        "attendance_date": record.get("date") or date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /attendance — List attendance logs (admin)
# ---------------------------------------------------------------------------

@router.get("", response_model=None)
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

    return {"total": total, "limit": limit, "offset": offset, "items": items}


# ---------------------------------------------------------------------------
# GET /attendance/analytics — Admin analytics summary
# ---------------------------------------------------------------------------

@router.get("/analytics")
def get_analytics(_user_id: str = Depends(get_request_user_id)) -> dict:
    """
    Returns summary statistics for the admin dashboard:
    total_students, present_count, denied_count, attendance_rate, by_session.
    """
    # Load all attendance records (up to 5000)
    _, all_records = appwrite_service.get_attendance(filters={"limit": 5000, "offset": 0})

    total_students = embedding_cache.size()
    present_count = sum(1 for r in all_records if r.get("status") == "present")
    denied_count = sum(1 for r in all_records if r.get("status") == "denied")
    total_submissions = len(all_records)
    attendance_rate = round((present_count / total_submissions * 100), 1) if total_submissions else 0.0

    # Aggregate by session
    by_session: dict[str, dict] = {}
    for record in all_records:
        sid = str(record.get("session_id") or "unknown")
        if sid not in by_session:
            by_session[sid] = {
                "session_id": sid,
                "class_name": record.get("class_name") or "",
                "present": 0,
                "denied": 0,
            }
        if record.get("status") == "present":
            by_session[sid]["present"] += 1
        else:
            by_session[sid]["denied"] += 1

    return {
        "total_students": total_students,
        "present_count": present_count,
        "denied_count": denied_count,
        "total_submissions": total_submissions,
        "attendance_rate": attendance_rate,
        "by_session": list(by_session.values()),
    }


# ---------------------------------------------------------------------------
# GET /attendance/export — CSV export
# ---------------------------------------------------------------------------

@router.get("/export")
def export_attendance_csv(
    search: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _user_id: str = Depends(get_request_user_id),
) -> Response:
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
