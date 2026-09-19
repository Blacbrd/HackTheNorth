from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.gemini import GeminiImageService
from app.storage import ImageStorage


def get_gemini_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GeminiImageService:
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )
    return cached_gemini_service(api_key, settings.gemini_image_model)


@lru_cache
def cached_gemini_service(api_key: str, model: str) -> GeminiImageService:
    return GeminiImageService(api_key=api_key, model=model)


@lru_cache
def _storage_for_directory(directory: str) -> ImageStorage:
    return ImageStorage(directory=Path(directory))


def get_image_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ImageStorage:
    return _storage_for_directory(str(settings.generated_directory))
