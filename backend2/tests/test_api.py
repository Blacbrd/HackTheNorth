def test_health(client) -> None:
    test_client, _ = client

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_simplify_returns_png_and_overwrites_named_files(client, png_bytes: bytes) -> None:
    test_client, output_directory = client

    response = test_client.post(
        "/api/simplify",
        files={"image": ("photo.png", png_bytes, "image/png")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(b"\x89PNG")
    assert (output_directory / "current-input.png").is_file()
    assert (output_directory / "current-drawing.png").is_file()


def test_rejects_non_image_upload(client) -> None:
    test_client, _ = client

    response = test_client.post(
        "/api/simplify",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload an image file."


def test_latest_result_is_missing_before_generation(client) -> None:
    test_client, _ = client

    response = test_client.get("/api/result")

    assert response.status_code == 404


def test_latest_result_returns_the_saved_drawing(client, png_bytes: bytes) -> None:
    test_client, _ = client
    test_client.post(
        "/api/simplify",
        files={"image": ("photo.png", png_bytes, "image/png")},
    )

    response = test_client.get("/api/result")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
