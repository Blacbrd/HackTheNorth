from pydantic import BaseModel, Field, field_validator


class ShelfResponse(BaseModel):
    shelf_number: int = Field(ge=1)
    items: list[str]


class ShelvesResponse(BaseModel):
    shelves: list[ShelfResponse]


class ItemRequest(BaseModel):
    item: str = Field(min_length=1, max_length=200)

    @field_validator("item")
    @classmethod
    def item_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Item must not be blank")
        return value
