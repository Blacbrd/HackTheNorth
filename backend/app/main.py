from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import recommendations, shelves, transcriptions

settings = get_settings()
app = FastAPI(title="Shelf Robot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(shelves.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(transcriptions.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
