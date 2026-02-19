from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/confluencr"
    db_auto_create: bool = True
    db_timezone: str = "Asia/Kolkata"
    db_operation_timeout_seconds: float = 8.0
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

    @field_validator("db_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DB_TIMEZONE must be a non-empty timezone name")
        return value

    @field_validator("db_operation_timeout_seconds")
    @classmethod
    def validate_db_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("DB_OPERATION_TIMEOUT_SECONDS must be > 0")
        return value


settings = Settings()
