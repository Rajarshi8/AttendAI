from pydantic import BaseModel, Field


class RecognizeRequest(BaseModel):
    frame: str | None = None
    frames: list[str] = Field(default_factory=list)
    threshold: float | None = Field(default=None, gt=0.0, le=1.0)
    require_liveness: bool = True


class RecognizeResponse(BaseModel):
    matched: bool
    live: bool
    similarity: float | None = None
    user: dict | None = None
    message: str
