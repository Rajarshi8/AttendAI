from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    images: list[str] = Field(min_length=10, max_length=20)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    user_id: str
    face_samples: int

    class Config:
        from_attributes = True
