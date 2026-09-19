from google import genai
from google.genai import types

from app.prompt import ROBOT_DRAWING_PROMPT


class GeminiImageError(RuntimeError):
    pass


class GeminiImageService:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def create_drawing(self, image: bytes) -> bytes:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[
                    ROBOT_DRAWING_PROMPT,
                    types.Part.from_bytes(data=image, mime_type="image/png"),
                ],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
        except Exception as exc:
            raise GeminiImageError("Gemini could not process the image.") from exc

        for part in response.parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and inline_data.data:
                return inline_data.data

        raise GeminiImageError("Gemini did not return an image. Try a clearer photo.")

    async def close(self) -> None:
        await self._client.aio.aclose()
