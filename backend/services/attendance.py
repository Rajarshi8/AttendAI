from __future__ import annotations

from datetime import date
from io import StringIO
import csv

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from models.attendance import Attendance
from models.user import User
from schemas.attendance import AttendanceItem


class AttendanceService:
    @staticmethod
    def mark_attendance(db: Session, user_id: int, status: str = "present") -> tuple[bool, Attendance, str]:
        today = date.today()
        existing = db.scalar(
            select(Attendance).where(
                and_(Attendance.user_id == user_id, Attendance.attendance_date == today)
            )
        )

        if existing:
            return False, existing, "Attendance already marked for today."

        record = Attendance(user_id=user_id, status=status, attendance_date=today)
        db.add(record)
        db.commit()
        db.refresh(record)
        return True, record, "Attendance marked successfully."

    @staticmethod
    def list_attendance(
        db: Session,
        search: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[int, list[AttendanceItem]]:
        query = (
            select(Attendance, User)
            .join(User, User.id == Attendance.user_id)
            .order_by(Attendance.timestamp.desc())
        )

        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(User.name).like(pattern),
                    func.lower(User.email).like(pattern),
                    func.lower(User.user_code).like(pattern),
                )
            )

        if start_date:
            query = query.where(Attendance.attendance_date >= start_date)
        if end_date:
            query = query.where(Attendance.attendance_date <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        rows = db.execute(query.offset(offset).limit(limit)).all()

        items = [
            AttendanceItem(
                id=attendance.id,
                user_id=user.id,
                user_name=user.name,
                user_code=user.user_code,
                email=user.email,
                status=attendance.status,
                timestamp=attendance.timestamp,
                attendance_date=attendance.attendance_date,
            )
            for attendance, user in rows
        ]
        return total, items

    @staticmethod
    def export_csv(items: list[AttendanceItem]) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Attendance ID", "User ID", "User Code", "Name", "Email", "Date", "Timestamp", "Status"])

        for item in items:
            writer.writerow(
                [
                    item.id,
                    item.user_id,
                    item.user_code,
                    item.user_name,
                    item.email,
                    item.attendance_date.isoformat(),
                    item.timestamp.isoformat(),
                    item.status,
                ]
            )

        return output.getvalue()


# Imported here to keep SQLAlchemy query composition readable.
from sqlalchemy import or_  # noqa: E402
