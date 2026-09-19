from app.schemas.recommendations import GeminiRecommendation


class RobotClient:
    """Replace send_pick_command with the robot's transport implementation."""

    def send_pick_command(self, recommendation: GeminiRecommendation) -> None:
        print(f"Dummy robot command: move to shelf {recommendation.shelf_number}, pick {recommendation.item}")
