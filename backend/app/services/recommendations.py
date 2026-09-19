from app.clients.gemini import GeminiClient, GeminiClientError
from app.clients.robot import RobotClient, RobotCommandError
from app.repositories.storage import ShelfNotFoundError, StorageRepository
from app.schemas.recommendations import GeminiRecommendation, RecommendationResponse
from app.services.robot_jobs import RobotJobService


class RecommendationUnavailableError(Exception):
    pass


class InvalidRecommendationError(Exception):
    pass


class RecommendationProviderError(Exception):
    pass


class RobotDispatchError(Exception):
    pass


class RecommendationService:
    def __init__(
        self,
        storage: StorageRepository,
        gemini: GeminiClient | None,
        robot: RobotClient,
        jobs: RobotJobService | None = None,
    ) -> None:
        self.storage = storage
        self.gemini = gemini
        self.robot = robot
        self.jobs = jobs

    def recommend(self, user_input: str, source: str, send_to_robot: bool = False) -> RecommendationResponse:
        if self.gemini is None:
            raise RecommendationUnavailableError("GEMINI_API_KEY is not configured")
        try:
            recommendation = self.gemini.recommend(self.storage.list_shelves(), user_input)
        except GeminiClientError as error:
            self._note_failure(user_input, "fault")
            raise RecommendationProviderError(str(error)) from error
        try:
            self._validate_against_inventory(recommendation)
        except InvalidRecommendationError:
            # The model named something the shelves do not have, which from the
            # volunteer's side looks the same as the item being gone.
            self._note_failure(user_input, "missing")
            raise
        if send_to_robot:
            try:
                self.robot.send_pick_command(recommendation)
            except RobotCommandError as error:
                self._note_failure(user_input, "fault")
                raise RobotDispatchError(str(error)) from error
            if self.jobs is not None:
                self.jobs.start(
                    recommendation,
                    user_input,
                    simulated=not self.robot.enabled,
                )
        return RecommendationResponse(**recommendation.model_dump(), source=source)

    def _note_failure(self, user_input: str, failure: str) -> None:
        if self.jobs is not None:
            self.jobs.record_failure(user_input, failure)

    def _validate_against_inventory(self, recommendation: GeminiRecommendation) -> None:
        try:
            items = self.storage.get_shelf(recommendation.shelf_number)
        except ShelfNotFoundError as error:
            raise InvalidRecommendationError("Gemini selected a shelf that does not exist") from error
        if recommendation.item.casefold() not in {item.casefold() for item in items}:
            raise InvalidRecommendationError("Gemini selected an item that is not on the reported shelf")
