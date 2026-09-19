from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.dependencies import get_transcription_service
from app.schemas.transcriptions import TranscriptionResponse
from app.services.transcriptions import (
    InvalidAudioUploadError,
    TranscriptionProviderError,
    TranscriptionService,
    TranscriptionUnavailableError,
)

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("", response_model=TranscriptionResponse)
async def transcribe(
    audio: Annotated[UploadFile, File(description="Audio recording to transcribe")],
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscriptionResponse:
    try:
        upload = await audio.read(service.max_audio_upload_bytes + 1)
        return await run_in_threadpool(service.transcribe, upload, audio.content_type)
    except InvalidAudioUploadError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None
    except TranscriptionUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except TranscriptionProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    finally:
        await audio.close()
