from datetime import date
from io import StringIO
import csv

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from middlewares import get_request_user_id
from schemas.attendance import AttendanceMarkRequest, AttendanceMarkResponse
from services.appwrite_client import appwrite_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("", response_model=AttendanceMarkResponse)
def mark_attendance(payload: AttendanceMarkRequest, user_id: str = Depends(get_request_user_id)):
    marked, record, message = appwrite_service.create_attendance(user_id=user_id, status=payload.status)

    users = appwrite_service.get_all_users()
    user_doc = next((doc for doc in users if str(doc.get("user_id")) == user_id), {})

    response_record = {
        "id": str(record.get("id") or record.get("$id")),
        "user_id": user_id,
        "user_name": user_doc.get("name") or "Unknown",
        "user_code": user_id,
        "email": user_doc.get("email") or "",
        "status": record.get("status") or payload.status,
        "timestamp": record.get("timestamp") or record.get("$createdAt"),
        "attendance_date": record.get("date") or date.today().isoformat(),
    }

    return AttendanceMarkResponse(marked=marked, message=message, record=response_record)


@router.get("")
def get_attendance_logs(
    search: str | None = Query(default=None),
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
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _user_id: str = Depends(get_request_user_id),
):
    _, items = appwrite_service.get_attendance(
        filters={
            "search": search,
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
    writer.writerow(["Attendance ID", "User ID", "User Code", "Name", "Email", "Date", "Timestamp", "Status"])

    for item in items:
        writer.writerow(
            [
                item.get("id"),
                item.get("user_id"),
                item.get("user_code"),
                item.get("user_name"),
                item.get("email"),
                item.get("attendance_date"),
                item.get("timestamp"),
                item.get("status"),
            ]
        )

    return output.getvalue()
