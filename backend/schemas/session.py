from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    class_name: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    radius_meters: float = Field(gt=1.0, le=2000.0)
    end_time: datetime | None = None


class SessionStopRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)


class SessionItem(BaseModel):
    session_id: str
    admin_id: str
    class_name: str
    start_time: datetime
    end_time: datetime | None = None
    latitude: float
    longitude: float
    radius_meters: float
    is_active: bool


class SessionStartResponse(BaseModel):
    message: str
    session: SessionItem


class SessionStopResponse(BaseModel):
    message: str
    session: SessionItem


class ActiveSessionResponse(BaseModel):
    session: SessionItem | None = None


class RoleGuardResponse(BaseModel):
    allowed: bool
    role: Literal["admin", "student"]
