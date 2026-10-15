from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./coastguard.db"
    load_demo_fixtures: bool = False
    app_env: str = "development"
    log_level: str = "INFO"
    advisory_max_age_hours: int = Field(default=24, gt=0, le=720)
    source_stale_after_hours: int = Field(default=24, gt=0, le=720)
    max_import_file_bytes: int = Field(default=5_000_000, gt=0, le=50_000_000)
    max_import_records: int = Field(default=5_000, gt=0, le=50_000)
    admin_api_token: str | None = None
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
