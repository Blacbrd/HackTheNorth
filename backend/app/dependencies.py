from functools import lru_cache
from pathlib import Path

from app.clients.gemini import GeminiClient
from app.clients.robot import RobotClient
from app.core.config import get_settings
from app.repositories.storage import StorageRepository
from app.services.recommendations import RecommendationService
from app.services.transcriptions import TranscriptionService


@lru_cache
def get_storage_repository() -> StorageRepository:
    return StorageRepository(Path(__file__).resolve().parent.parent / "storage.json")


@lru_cache
def get_recommendation_service() -> RecommendationService:
    settings = get_settings()
    gemini = GeminiClient(settings.gemini_api_key, settings.gemini_model) if settings.gemini_api_key else None
    return RecommendationService(get_storage_repository(), gemini, RobotClient())


@lru_cache
def get_transcription_service() -> TranscriptionService:
    settings = get_settings()
    gemini = GeminiClient(settings.gemini_api_key, settings.gemini_model) if settings.gemini_api_key else None
    return TranscriptionService(gemini, settings.max_audio_upload_bytes)
