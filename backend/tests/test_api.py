from pathlib import Path

from fastapi.testclient import TestClient

from app.clients.gemini import GeminiClientError
from app.clients.robot import RobotClient
from app.dependencies import get_recommendation_service, get_storage_repository, get_transcription_service
from app.main import app
from app.repositories.storage import StorageRepository
from app.schemas.recommendations import GeminiRecommendation
from app.services.recommendations import RecommendationService
from app.services.transcriptions import TranscriptionService


class FakeGemini:
    def recommend(self, shelves: dict[int, list[str]], user_input: str) -> GeminiRecommendation:
        return GeminiRecommendation(shelf_number=1, item="peas")

    def transcribe(self, audio: bytes, mime_type: str) -> str:
        return "I need something gluten free"


class InvalidShelfGemini:
    def recommend(self, shelves: dict[int, list[str]], user_input: str) -> GeminiRecommendation:
        return GeminiRecommendation(shelf_number=99, item="peas")


class FailingTranscriptionGemini:
    def transcribe(self, audio: bytes, mime_type: str) -> str:
        raise GeminiClientError("Gemini could not transcribe the audio")


class RecordingRobot(RobotClient):
    def __init__(self) -> None:
        self.commands: list[GeminiRecommendation] = []

    def send_pick_command(self, recommendation: GeminiRecommendation) -> None:
        self.commands.append(recommendation)


def build_client(tmp_path: Path, robot: RobotClient | None = None) -> TestClient:
    storage = StorageRepository(tmp_path / "storage.json")
    storage.path.write_text('{"1": ["peas"], "2": ["rice"]}', encoding="utf-8")
    service = RecommendationService(storage, FakeGemini(), robot or RobotClient())
    app.dependency_overrides[get_storage_repository] = lambda: storage
    app.dependency_overrides[get_recommendation_service] = lambda: service
    return TestClient(app)


def test_shelf_item_lifecycle(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        assert client.get("/api/shelves").json()["shelves"][0]["items"] == ["peas"]
        assert client.post("/api/shelves/1/items", json={"item": "banana"}).status_code == 201
        assert client.delete("/api/shelves/1/items/banana").json()["items"] == ["peas"]

        first_duplicate = client.post("/api/shelves/1/items", json={"item": "peas"})
        second_duplicate = client.post("/api/shelves/1/items", json={"item": "PeAs"})
        assert first_duplicate.status_code == 201
        assert second_duplicate.json()["items"] == ["peas", "peas", "PeAs"]
        assert client.delete("/api/shelves/1/items/peas").json()["items"] == ["peas", "PeAs"]
        assert client.delete("/api/shelves/1/items/PeAs").json()["items"] == ["peas"]

        assert client.post("/api/shelves/1/items", json={"item": "   "}).status_code == 422
    app.dependency_overrides.clear()


def test_invalid_gemini_shelf_is_reported_as_bad_gateway(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        storage = app.dependency_overrides[get_storage_repository]()
        app.dependency_overrides[get_recommendation_service] = lambda: RecommendationService(storage, InvalidShelfGemini(), RobotClient())
        response = client.post("/api/recommendations/app", json={"user_input": "peas"})
    assert response.status_code == 502
    app.dependency_overrides.clear()


def test_both_recommendation_origins_reuse_service(tmp_path: Path) -> None:
    robot = RecordingRobot()
    with build_client(tmp_path, robot) as client:
        app_result = client.post("/api/recommendations/app", json={"user_input": "a vegetable"})
        robot_result = client.post("/api/recommendations/robot", json={"user_input": "a vegetable"})
    assert app_result.json() == {"shelf_number": 1, "item": "peas", "source": "app"}
    assert robot_result.json() == {"shelf_number": 1, "item": "peas", "source": "robot"}
    assert robot.commands == [GeminiRecommendation(shelf_number=1, item="peas")]
    app.dependency_overrides.clear()


def test_transcription_returns_plain_text_and_validates_uploads(tmp_path: Path) -> None:
    app.dependency_overrides[get_transcription_service] = lambda: TranscriptionService(FakeGemini(), 10)
    with TestClient(app) as client:
        response = client.post(
            "/api/transcriptions",
            files={"audio": ("request.webm", b"audio", "audio/webm; codecs=opus")},
        )
        unsupported = client.post("/api/transcriptions", files={"audio": ("request.txt", b"text", "text/plain")})
        oversized = client.post("/api/transcriptions", files={"audio": ("request.m4a", b"too much audio", "audio/m4a")})
    assert response.json() == {"text": "I need something gluten free"}
    assert unsupported.status_code == 415
    assert oversized.status_code == 413
    app.dependency_overrides.clear()


def test_transcription_maps_missing_key_and_provider_errors(tmp_path: Path) -> None:
    audio = {"audio": ("request.m4a", b"audio", "audio/m4a")}
    app.dependency_overrides[get_transcription_service] = lambda: TranscriptionService(None, 10)
    with TestClient(app) as client:
        unavailable = client.post("/api/transcriptions", files=audio)

    app.dependency_overrides[get_transcription_service] = lambda: TranscriptionService(FailingTranscriptionGemini(), 10)
    with TestClient(app) as client:
        provider_failure = client.post("/api/transcriptions", files=audio)

    assert unavailable.status_code == 503
    assert provider_failure.status_code == 502
    app.dependency_overrides.clear()
