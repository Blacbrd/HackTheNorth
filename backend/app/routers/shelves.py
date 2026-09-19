from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_storage_repository
from app.repositories.storage import (
    ItemNotFoundError,
    ShelfAlreadyExistsError,
    ShelfNotFoundError,
    StorageRepository,
)
from app.schemas.shelves import ItemRequest, ShelfCreateRequest, ShelfResponse, ShelvesResponse

router = APIRouter(prefix="/shelves", tags=["shelves"])


def _response(shelf_number: int, items: list[str]) -> ShelfResponse:
    return ShelfResponse(shelf_number=shelf_number, items=items)


@router.get("", response_model=ShelvesResponse)
def list_shelves(repository: StorageRepository = Depends(get_storage_repository)) -> ShelvesResponse:
    shelves = repository.list_shelves()
    return ShelvesResponse(shelves=[_response(number, items) for number, items in sorted(shelves.items())])


@router.post("", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
def create_shelf(
    request: ShelfCreateRequest | None = None,
    repository: StorageRepository = Depends(get_storage_repository),
) -> ShelfResponse:
    try:
        shelf_number, items = repository.create_shelf(request.shelf_number if request else None)
    except ShelfAlreadyExistsError:
        raise HTTPException(status_code=409, detail="That shelf already exists") from None
    return _response(shelf_number, items)


@router.delete("/{shelf_number}", response_model=ShelvesResponse)
def delete_shelf(shelf_number: int, repository: StorageRepository = Depends(get_storage_repository)) -> ShelvesResponse:
    """Returns what is left, so the app can redraw the list from one round trip."""
    try:
        shelves = repository.delete_shelf(shelf_number)
    except ShelfNotFoundError:
        raise HTTPException(status_code=404, detail="Shelf not found") from None
    return ShelvesResponse(shelves=[_response(number, items) for number, items in sorted(shelves.items())])


@router.get("/{shelf_number}", response_model=ShelfResponse)
def get_shelf(shelf_number: int, repository: StorageRepository = Depends(get_storage_repository)) -> ShelfResponse:
    try:
        return _response(shelf_number, repository.get_shelf(shelf_number))
    except ShelfNotFoundError:
        raise HTTPException(status_code=404, detail="Shelf not found") from None


@router.post("/{shelf_number}/items", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
def add_item(shelf_number: int, request: ItemRequest, repository: StorageRepository = Depends(get_storage_repository)) -> ShelfResponse:
    try:
        items: list[str] = []
        for _ in range(request.quantity):
            items = repository.add_item(shelf_number, request.item)
        return _response(shelf_number, items)
    except ShelfNotFoundError:
        raise HTTPException(status_code=404, detail="Shelf not found") from None


@router.delete("/{shelf_number}/items/{item}", response_model=ShelfResponse)
def remove_item(shelf_number: int, item: str, repository: StorageRepository = Depends(get_storage_repository)) -> ShelfResponse:
    try:
        return _response(shelf_number, repository.remove_item(shelf_number, item))
    except ShelfNotFoundError:
        raise HTTPException(status_code=404, detail="Shelf not found") from None
    except ItemNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found on shelf") from None
