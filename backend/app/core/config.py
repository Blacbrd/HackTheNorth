from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    max_audio_upload_bytes: int = 10 * 1024 * 1024
    cors_origins: str = "http://localhost:8081,http://localhost:19006,exp://localhost:8081"
    # The app resolves the API from whichever host served its bundle, so on a
    # phone that is a LAN address rather than localhost and the literal origins
    # above never match. Allow any host on Expo's dev ports instead.
    cors_origin_regex: str = r"^(https?|exp)://[^/\s]+:(8081|19000|19006)$"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
