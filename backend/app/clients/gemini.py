from google import genai
from google.genai import types

from app.schemas.recommendations import GeminiRecommendation, GeminiRecommendationList


SYSTEM_PROMPT = """You choose exactly one stored grocery item for a robot to fetch.
Use the user's request and the supplied shelves. Respect dietary needs: peas and other vegetables
are vegetarian/vegan, avoid meat for vegetarian or vegan requests, and only select gluten-free
pasta when the item itself says gluten-free. Never invent an item or shelf. Return only the
structured shelf_number and item selected from the supplied inventory."""

TWO_ITEM_SYSTEM_PROMPT = """You choose exactly TWO distinct stored grocery items for a robot to
fetch in one trip. They may be on the same shelf or different shelves, but together they must
satisfy the user's request. Use the user's request and the supplied shelves. Respect dietary
needs: peas and other vegetables are vegetarian/vegan, avoid meat for vegetarian or vegan
requests, and only select gluten-free pasta when the item itself says gluten-free. Never invent
an item or shelf. Return only the structured list of exactly two items, each with its
shelf_number and item, selected from the supplied inventory."""

TRANSCRIPTION_SYSTEM_PROMPT = """Transcribe the supplied audio faithfully.
Return only the spoken words as plain text. Do not add labels, commentary, or punctuation that
was not spoken. If the audio is unintelligible, return an empty response."""


class GeminiClientError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def recommend(
        self, shelves: dict[int, list[str]], user_input: str, count: int = 1
    ) -> list[GeminiRecommendation]:
        inventory = {str(number): items for number, items in shelves.items()}
        contents = f"Inventory: {inventory}\nUser request: {user_input}"
        try:
            if count == 2:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=TWO_ITEM_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=GeminiRecommendationList,
                    ),
                )
                return GeminiRecommendationList.model_validate_json(response.text).items
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=GeminiRecommendation,
                ),
            )
            return [GeminiRecommendation.model_validate_json(response.text)]
        except Exception as error:
            raise GeminiClientError("Gemini could not produce a valid recommendation") from error

    def transcribe(self, audio: bytes, mime_type: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[types.Part.from_bytes(data=audio, mime_type=mime_type)],
                config=types.GenerateContentConfig(system_instruction=TRANSCRIPTION_SYSTEM_PROMPT),
            )
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Gemini returned an empty transcript")
            return text
        except Exception as error:
            raise GeminiClientError("Gemini could not transcribe the audio") from error
