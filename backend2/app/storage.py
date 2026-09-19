from pathlib import Path

INPUT_FILENAME = "current-input.png"
DRAWING_FILENAME = "current-drawing.png"


class ImageStorage:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    @property
    def drawing_path(self) -> Path:
        return self.directory / DRAWING_FILENAME

    def save_input(self, data: bytes) -> Path:
        return self._replace(INPUT_FILENAME, data)

    def save_drawing(self, data: bytes) -> Path:
        return self._replace(DRAWING_FILENAME, data)

    def _replace(self, filename: str, data: bytes) -> Path:
        destination = self.directory / filename
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(destination)
        return destination
