from io import BytesIO

from PIL import Image

from app.images import normalize_generated_image


def test_generated_image_is_reduced_to_pure_black_and_white() -> None:
    source = BytesIO()
    image = Image.new("RGB", (5, 5), (240, 220, 210))
    image.putpixel((2, 2), (20, 30, 40))
    image.save(source, format="PNG")

    result = normalize_generated_image(source.getvalue())

    with Image.open(BytesIO(result)) as normalized:
        values = set(normalized.convert("L").get_flattened_data())
    assert values <= {0, 255}
