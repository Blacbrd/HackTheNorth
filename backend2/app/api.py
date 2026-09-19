import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response

from app.config import Settings, get_settings
from app.dependencies import get_gemini_service, get_image_storage
from app.gemini import GeminiImageError, GeminiImageService
from app.images import InvalidImageError, normalize_generated_image, normalize_upload
from app.storage import ImageStorage

router = APIRouter()
generation_lock = asyncio.Lock()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/simplify",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "Simplified line drawing"},
        400: {"description": "Invalid image"},
        413: {"description": "Image too large"},
        502: {"description": "Gemini generation failed"},
    },
)
async def simplify_image(
    image: Annotated[UploadFile, File(description="Photo to simplify")],
    settings: Annotated[Settings, Depends(get_settings)],
    gemini: Annotated[GeminiImageService, Depends(get_gemini_service)],
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> Response:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload an image file.")

    upload = await image.read(settings.max_upload_bytes + 1)
    await image.close()
    if len(upload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The image is larger than the configured upload limit.",
        )

    try:
        normalized_input = await asyncio.to_thread(
            normalize_upload, upload, settings.max_image_dimension
        )
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    async with generation_lock:
        try:
            generated = await gemini.create_drawing(normalized_input)
            normalized_output = await asyncio.to_thread(normalize_generated_image, generated)
        except (GeminiImageError, InvalidImageError) as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        await asyncio.to_thread(storage.save_input, normalized_input)
        await asyncio.to_thread(storage.save_drawing, normalized_output)

    return Response(
        content=normalized_output,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="current-drawing.png"',
        },
    )


@router.get(
    "/api/result",
    response_class=FileResponse,
    responses={404: {"description": "No drawing has been generated yet"}},
)
async def latest_result(
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> FileResponse:
    if not storage.drawing_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No drawing exists yet.")

    return FileResponse(
        storage.drawing_path,
        media_type="image/png",
        filename="current-drawing.png",
        headers={"Cache-Control": "no-store"},
    )
