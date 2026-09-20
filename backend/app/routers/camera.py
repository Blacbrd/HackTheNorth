"""Proxies the robot's head camera so the phone only ever talks to this API.

The robot's camera server (`hampy_demo/camera_web.py`, which serves single
JPEGs from /snapshot/<topic>.jpg) is only reachable on the robot's own
LAN/hotspot; the phone is not always on that network, and even when it is,
pointing the app straight at robot hardware
means a robot IP change breaks the app instead of a .env value. Proxying
through here also lets `/robot/camera/status` report reachability the same
way the snapshot endpoint would fail, without the phone needing to know what
"unreachable" looks like for this particular camera server.
"""

from __future__ import annotations

import asyncio
import io

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from PIL import Image

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/robot", tags=["camera"])

_CAMERA_UNREACHABLE = "The robot camera is not reachable."
# `camera.head.jpeg` is a stereo pair published as one 2560x960 frame: two
# 1280x960 eyes joined side by side. Anything at least this wide relative to
# its height is assumed to be such a pair.
_STEREO_MIN_RATIO = 2.0
# Re-encode quality for the cropped eye. The robot sends ~400KB frames; one
# eye at this quality lands near a quarter of that, which is the difference
# between a feed that keeps up over the hotspot and one that does not.
_JPEG_QUALITY = 80


def _snapshot_url(settings: Settings) -> str:
    return f"{settings.robot_camera_url}/snapshot/{settings.robot_camera_topic}.jpg"


def _left_eye(frame: bytes) -> bytes:
    """Crops a stereo frame down to its left eye.

    The app shows the feed in a 4:3 box. Handing it the full 8:3 pair means
    `resizeMode="cover"` crops to the *centre* of the pair, which is the right
    half of one eye butted against the left half of the other -- a seam straight
    down the middle of the picture. Cropping here rather than in the app also
    means the smaller image is what crosses the network.

    A frame that is not a stereo pair, or that Pillow cannot read, is passed
    through untouched: a correct-looking feed matters more than a cropped one.
    """
    try:
        with Image.open(io.BytesIO(frame)) as image:
            width, height = image.size
            if height <= 0 or width / height < _STEREO_MIN_RATIO:
                return frame
            eye = image.crop((0, 0, width // 2, height))
            buffer = io.BytesIO()
            eye.convert("RGB").save(buffer, format="JPEG", quality=_JPEG_QUALITY)
            return buffer.getvalue()
    except OSError:
        return frame


@router.get("/camera.jpg")
async def camera_snapshot(settings: Settings = Depends(get_settings)) -> Response:
    try:
        async with httpx.AsyncClient(timeout=settings.robot_camera_timeout_seconds) as http_client:
            response = await http_client.get(_snapshot_url(settings))
            response.raise_for_status()
    except httpx.HTTPError:
        # Covers connect failures, timeouts, and non-2xx status alike -- from
        # the phone's side an unreachable camera and a camera erroring out
        # look the same, and neither should ever surface as a 500.
        raise HTTPException(status_code=503, detail=_CAMERA_UNREACHABLE) from None
    # Decoding and re-encoding a 400KB JPEG is only a few milliseconds, but it
    # is CPU-bound, and at several frames a second across a couple of phones
    # that is enough to stall the event loop. Hand it to a worker thread.
    frame = await asyncio.to_thread(_left_eye, response.content)
    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/camera/status")
async def camera_status(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    url = _snapshot_url(settings)
    try:
        async with httpx.AsyncClient(timeout=settings.robot_camera_timeout_seconds) as http_client:
            response = await http_client.get(url)
            available = response.is_success
    except httpx.HTTPError:
        available = False
    return {"available": available, "url": url}
