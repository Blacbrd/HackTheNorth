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
    robot_enabled: bool = False
    robot_transport: str = "local"
    robot_host: str = "bracketbot-0186.local"
    robot_user: str = "bracketbot"
    robot_app_dir: str = "/home/bracketbot/bbapps/hampy_demo"
    robot_station_by_shelf: str = "1:table_1,2:table_2,3:table_3"
    robot_dropoff_station: str = "table_2"
    robot_command_timeout_seconds: int = 240
    # The workflow command run inside robot_app_dir. Overridable from .env so a
    # robot-side rename (or an added --flag) never needs a code change here.
    robot_command: str = "uv run transfer_both.py --execute --yes"
    # Two-item mode asks Gemini for a pair and runs the four-stage job instead
    # of the three-stage single-item one. Off by default for the simpler demo.
    robot_two_item_mode: bool = False
    robot_camera_url: str = "http://172.20.10.3:8082"
    robot_camera_topic: str = "camera.head.jpeg"
    robot_camera_timeout_seconds: float = 4.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
