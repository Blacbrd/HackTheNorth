import logging

from google import genai
from google.genai import types

from app.prompt import ROBOT_DRAWING_PROMPT

logger = logging.getLogger(__name__)


class GeminiImageError(RuntimeError):
    pass


def describe_failure(exc: Exception) -> str:
    """Turn an SDK exception into something the person holding the phone can act on.

    Only fixed strings are returned. The exception text can carry request
    details, so it goes to the log rather than to the client.
    """
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        if "limit: 0" in text:
            return (
                "This Gemini key has no image-generation quota. Image models are not "
                "offered on the free tier, so the project needs billing enabled."
            )
        return "Gemini is rate limited right now. Wait a few seconds and try again."
    if "PERMISSION_DENIED" in text or "API key not valid" in text or "403" in text:
        return "Gemini rejected the API key."
    if "NOT_FOUND" in text or "404" in text:
        return "The configured Gemini model is not available to this API key."
    return "Gemini could not process the image."


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
            # The reason matters far too much to drop: a quota wall, a rejected
            # key and a bad model name all used to surface as the same sentence.
            logger.exception("Gemini image generation failed (model=%s)", self._model)
            raise GeminiImageError(describe_failure(exc)) from exc

        for part in response.parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and inline_data.data:
                return inline_data.data

        raise GeminiImageError("Gemini did not return an image. Try a clearer photo.")

    async def close(self) -> None:
        await self._client.aio.aclose()
