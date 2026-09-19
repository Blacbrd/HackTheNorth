from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: SecretStr = SecretStr("")
    gemini_image_model: str = "gemini-3.1-flash-image"
    allowed_origins: str = "http://localhost:8081,http://localhost:8082"
    max_upload_bytes: int = 12 * 1024 * 1024
    max_image_dimension: int = 2048
    generated_directory: Path = BACKEND_ROOT / "generated"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
