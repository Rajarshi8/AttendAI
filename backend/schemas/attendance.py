from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceMarkRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    frame: str | None = None
    frames: list[str] = Field(default_factory=list)
    threshold: float | None = Field(default=None, gt=0.0, le=1.0)
    require_liveness: bool = True


class AttendanceItem(BaseModel):
    id: str
    user_id: str
    session_id: str | None = None
    user_name: str
    user_code: str
    email: str
    status: str
    distance: float | None = None
    timestamp: datetime
    attendance_date: date


class AttendanceMarkResponse(BaseModel):
    marked: bool
    message: str
    record: AttendanceItem | None = None
