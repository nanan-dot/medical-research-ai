"""医学科研智能助手平台 — FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.common.exception_handlers import app_error_handler
from app.common.exceptions import AppError
from app.core.config import settings
from app.core.database import engine
from app.modules.document_anchor.extractor_runner import (
    ExtractorUnavailableError,
    PdfTextItemExtractor,
)
from app.modules.recommendation.v5_scheduler import RecommendationScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        app.state.document_anchor_capability = {
            "status": "AVAILABLE",
            "toolchain": await PdfTextItemExtractor().probe(),
        }
    except ExtractorUnavailableError:
        app.state.document_anchor_capability = {
            "status": "UNAVAILABLE",
            "code": "anchor_extractor_unavailable",
        }
    RecommendationScheduler.start_recovery_loop()
    try:
        yield
    finally:
        await RecommendationScheduler.stop_recovery_loop()
        await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}
