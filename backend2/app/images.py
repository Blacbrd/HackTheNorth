from io import BytesIO

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

MAX_INPUT_PIXELS = 40_000_000


class InvalidImageError(ValueError):
    pass


def normalize_upload(data: bytes, max_dimension: int) -> bytes:
    try:
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > MAX_INPUT_PIXELS:
                raise InvalidImageError("The image dimensions are too large to process.")
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
    except InvalidImageError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("The uploaded file is not a readable image.") from exc

    if image.width < 2 or image.height < 2:
        raise InvalidImageError("The image is too small to process.")

    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def normalize_generated_image(data: bytes) -> bytes:
    try:
        with Image.open(BytesIO(data)) as source:
            source.load()
            grayscale = ImageOps.autocontrast(source.convert("L"), cutoff=(0, 1))
            softened = grayscale.filter(ImageFilter.MedianFilter(size=3))
            image = softened.point(lambda pixel: 255 if pixel >= 200 else 0).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("Gemini returned image data that could not be decoded.") from exc

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
