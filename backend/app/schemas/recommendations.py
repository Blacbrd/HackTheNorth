from pydantic import BaseModel, Field, field_validator


class RecommendationRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=2_000)

    @field_validator("user_input")
    @classmethod
    def user_input_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("User input must not be blank")
        return value


class GeminiRecommendation(BaseModel):
    shelf_number: int = Field(ge=1)
    item: str = Field(min_length=1)

    @field_validator("item")
    @classmethod
    def item_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Item must not be blank")
        return value


class GeminiRecommendationList(BaseModel):
    """Wraps Gemini's two-item picks so response_schema has a single object to
    fill in, rather than a bare list Gemini's structured output cannot target."""

    items: list[GeminiRecommendation] = Field(min_length=1, max_length=2)


class RecommendationResponse(BaseModel):
    items: list[GeminiRecommendation]
    source: str
    # Mirror items[0] so a client that only ever knew about one item keeps
    # working without change.
    shelf_number: int | None = None
    item: str | None = None
