from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/confluencr"
    db_auto_create: bool = True
    processing_delay_seconds: int = 30
    processing_stale_timeout_seconds: int = 120
    log_level: str = "INFO"

    @field_validator("processing_delay_seconds")
    @classmethod
    def validate_delay(cls, value: int) -> int:
        if value < 0:
            raise ValueError("PROCESSING_DELAY_SECONDS must be >= 0")
        return value

    @field_validator("processing_stale_timeout_seconds")
    @classmethod
    def validate_stale_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("PROCESSING_STALE_TIMEOUT_SECONDS must be > 0")
        return value


settings = Settings()
