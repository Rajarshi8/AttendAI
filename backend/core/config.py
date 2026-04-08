from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AttendAI Face Recognition API"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"

    cors_origins: list[str] = ["http://localhost:3000"]
    appwrite_endpoint: str = "https://nyc.cloud.appwrite.io/v1"
    appwrite_project_id: str = "69d53599001c62969125"
    appwrite_api_key: str = ""
    appwrite_database_id: str = ""
    appwrite_users_collection_id: str = ""
    appwrite_attendance_collection_id: str = ""

    face_model: str = "Facenet512"
    default_similarity_threshold: float = 0.6
    frame_process_stride: int = 3
    max_frame_width: int = 640
    liveness_min_frames: int = 6
    liveness_min_displacement: float = 15.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
