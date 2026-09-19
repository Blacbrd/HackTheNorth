from pydantic import BaseModel, Field, field_validator


class ShelfResponse(BaseModel):
    shelf_number: int = Field(ge=1)
    items: list[str]


class ShelvesResponse(BaseModel):
    shelves: list[ShelfResponse]


class ShelfCreateRequest(BaseModel):
    # Omit the number to append the next one; give one to fill a gap.
    shelf_number: int | None = Field(default=None, ge=1)


class ItemRequest(BaseModel):
    item: str = Field(min_length=1, max_length=200)
    # Quantity is how many copies of the name the shelf holds, because a shelf
    # is a flat list. Restocking five of something is one request, not five.
    quantity: int = Field(default=1, ge=1, le=99)

    @field_validator("item")
    @classmethod
    def item_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Item must not be blank")
        return value
