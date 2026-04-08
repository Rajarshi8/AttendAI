from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceMarkRequest(BaseModel):
    status: str = Field(default="present", max_length=30)


class AttendanceItem(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_code: str
    email: str
    status: str
    timestamp: datetime
    attendance_date: date


class AttendanceMarkResponse(BaseModel):
    marked: bool
    message: str
    record: AttendanceItem | None = None
