from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import get_gemini_service, get_image_storage
from app.main import app
from app.storage import ImageStorage


class FakeGeminiService:
    def __init__(self, output: bytes) -> None:
        self.output = output

    async def create_drawing(self, image: bytes) -> bytes:
        assert image.startswith(b"\x89PNG")
        return self.output


@pytest.fixture
def png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (16, 12), "white").save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def client(tmp_path: Path, png_bytes: bytes):
    settings = Settings(
        gemini_api_key="test-key",
        generated_directory=tmp_path,
        max_upload_bytes=1024 * 1024,
    )
    storage = ImageStorage(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_image_storage] = lambda: storage
    app.dependency_overrides[get_gemini_service] = lambda: FakeGeminiService(png_bytes)

    with TestClient(app) as test_client:
        yield test_client, tmp_path

    app.dependency_overrides.clear()
