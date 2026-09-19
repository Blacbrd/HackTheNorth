import json
import os
import tempfile
from pathlib import Path
from threading import RLock


class ShelfNotFoundError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class StorageRepository:
    """Owns the small JSON store and replaces it atomically after every change."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._mutation_lock = RLock()

    def list_shelves(self) -> dict[int, list[str]]:
        with self.path.open(encoding="utf-8") as file:
            raw = json.load(file)
        return {int(number): list(items) for number, items in raw.items()}

    def get_shelf(self, shelf_number: int) -> list[str]:
        shelves = self.list_shelves()
        if shelf_number not in shelves:
            raise ShelfNotFoundError(shelf_number)
        return shelves[shelf_number]

    def add_item(self, shelf_number: int, item: str) -> list[str]:
        with self._mutation_lock:
            shelves = self.list_shelves()
            if shelf_number not in shelves:
                raise ShelfNotFoundError(shelf_number)
            normalized_item = item.strip()
            shelves[shelf_number].append(normalized_item)
            self._write(shelves)
            return shelves[shelf_number]

    def remove_item(self, shelf_number: int, item: str) -> list[str]:
        with self._mutation_lock:
            shelves = self.list_shelves()
            if shelf_number not in shelves:
                raise ShelfNotFoundError(shelf_number)
            requested_item = item.strip()
            matching_item = next(
                (
                    existing
                    for existing in shelves[shelf_number]
                    if existing == requested_item
                ),
                None,
            )
            if matching_item is None:
                matching_item = next(
                    (
                        existing
                        for existing in shelves[shelf_number]
                        if existing.casefold() == requested_item.casefold()
                    ),
                    None,
                )
            if matching_item is None:
                raise ItemNotFoundError(item)
            shelves[shelf_number].remove(matching_item)
            self._write(shelves)
            return shelves[shelf_number]

    def _write(self, shelves: dict[int, list[str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="storage-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump({str(number): items for number, items in shelves.items()}, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_name, self.path)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
