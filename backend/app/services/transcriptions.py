from app.clients.gemini import GeminiClient, GeminiClientError
from app.schemas.transcriptions import TranscriptionResponse


SUPPORTED_AUDIO_MIME_TYPES = frozenset(
    {
        "audio/aac",
        "audio/m4a",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        "audio/x-wav",
        "audio/x-m4a",
        "audio/3gpp",
    }
)


class InvalidAudioUploadError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class TranscriptionUnavailableError(Exception):
    pass


class TranscriptionProviderError(Exception):
    pass


class TranscriptionService:
    def __init__(self, gemini: GeminiClient | None, max_audio_upload_bytes: int) -> None:
        self.gemini = gemini
        self.max_audio_upload_bytes = max_audio_upload_bytes

    def transcribe(self, audio: bytes, mime_type: str | None) -> TranscriptionResponse:
        normalized_mime_type = self._validate_upload(audio, mime_type)
        if self.gemini is None:
            raise TranscriptionUnavailableError("GEMINI_API_KEY is not configured")
        try:
            text = self.gemini.transcribe(audio, normalized_mime_type)
        except GeminiClientError as error:
            raise TranscriptionProviderError(str(error)) from error
        return TranscriptionResponse(text=text)

    def _validate_upload(self, audio: bytes, mime_type: str | None) -> str:
        normalized_mime_type = (mime_type or "").partition(";")[0].strip().lower()
        if normalized_mime_type not in SUPPORTED_AUDIO_MIME_TYPES:
            raise InvalidAudioUploadError("Unsupported audio MIME type", status_code=415)
        if not audio:
            raise InvalidAudioUploadError("Audio upload is empty", status_code=422)
        if len(audio) > self.max_audio_upload_bytes:
            raise InvalidAudioUploadError("Audio upload exceeds the configured size limit", status_code=413)
        return normalized_mime_type
