from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    images: list[str] = Field(min_length=10, max_length=20)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    user_id: str
    role: Literal["admin", "student"] = "student"
    face_samples: int


class CurrentUserResponse(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    role: Literal["admin", "student"] = "student"
    has_embedding: bool

    class Config:
        from_attributes = True
