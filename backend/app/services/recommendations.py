from app.clients.gemini import GeminiClient, GeminiClientError
from app.clients.robot import RobotClient
from app.repositories.storage import ShelfNotFoundError, StorageRepository
from app.schemas.recommendations import GeminiRecommendation, RecommendationResponse


class RecommendationUnavailableError(Exception):
    pass


class InvalidRecommendationError(Exception):
    pass


class RecommendationProviderError(Exception):
    pass


class RecommendationService:
    def __init__(self, storage: StorageRepository, gemini: GeminiClient | None, robot: RobotClient) -> None:
        self.storage = storage
        self.gemini = gemini
        self.robot = robot

    def recommend(self, user_input: str, source: str, send_to_robot: bool = False) -> RecommendationResponse:
        if self.gemini is None:
            raise RecommendationUnavailableError("GEMINI_API_KEY is not configured")
        try:
            recommendation = self.gemini.recommend(self.storage.list_shelves(), user_input)
        except GeminiClientError as error:
            raise RecommendationProviderError(str(error)) from error
        self._validate_against_inventory(recommendation)
        if send_to_robot:
            self.robot.send_pick_command(recommendation)
        return RecommendationResponse(**recommendation.model_dump(), source=source)

    def _validate_against_inventory(self, recommendation: GeminiRecommendation) -> None:
        try:
            items = self.storage.get_shelf(recommendation.shelf_number)
        except ShelfNotFoundError as error:
            raise InvalidRecommendationError("Gemini selected a shelf that does not exist") from error
        if recommendation.item.casefold() not in {item.casefold() for item in items}:
            raise InvalidRecommendationError("Gemini selected an item that is not on the reported shelf")
