from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import get_settings
from app.dependencies import cached_gemini_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value()
    try:
        yield
    finally:
        if api_key:
            await cached_gemini_service(api_key, settings.gemini_image_model).close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Robot Sketch API",
        version="0.1.0",
        description="Turns one photo into a simple black-and-white drawing with Gemini.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
