from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AttendAI Face Recognition API"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"

    # Stored as a raw comma-separated string to avoid pydantic-settings 2.x
    # treating list[str] fields as JSON-only. Parsed via the property below.
    cors_origins_raw: str = "http://localhost:3000"
    appwrite_endpoint: str = "https://nyc.cloud.appwrite.io/v1"
    appwrite_project_id: str = "69d53599001c62969125"
    appwrite_api_key: str = ""
    appwrite_database_id: str = ""
    appwrite_users_collection_id: str = ""
    appwrite_sessions_collection_id: str = ""
    appwrite_attendance_collection_id: str = ""

    # AI / Face recognition
    face_model: str = "Facenet512"
    default_similarity_threshold: float = 0.6
    frame_process_stride: int = 3
    max_frame_width: int = 640
    liveness_min_frames: int = 6
    liveness_min_displacement: float = 15.0

    # Embedding cache
    cache_refresh_interval_minutes: int = 10

    # Geofence
    geofence_buffer_meters: float = 10.0
    gps_accuracy_limit_meters: float = 50.0

    # Rate limiting
    rate_limit_attendance: str = "10/minute"
    rate_limit_recognize: str = "20/minute"

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS_RAW into a list."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
