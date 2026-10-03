from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from app.model_manager import get_manager
from app.providers.base import TranslationProvider
from app.providers.indictrans2 import IndicTrans2Provider
from app.schemas import TranslationRequest, TranslationResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

translation_provider: TranslationProvider = IndicTrans2Provider()
NOT_READY_MESSAGE = "Translation is unavailable until an IndicTrans2 checkpoint is configured."


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager = get_manager()
    if isinstance(translation_provider, IndicTrans2Provider):
        manager.warm_up()
    yield
    manager.unload()


app = FastAPI(
    title="BharatVoice AI Service",
    version="0.2.0",
    description="Private AI inference API; provider weights are configured separately.",
    lifespan=lifespan,
)


def _not_ready_http_exception() -> HTTPException:
    detail: dict[str, object] = {
        "code": "translation_provider_not_ready",
        "message": NOT_READY_MESSAGE,
    }
    provider = translation_provider
    if isinstance(provider, IndicTrans2Provider):
        detail["provider"] = provider.status
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check; it does not imply that model weights are loaded."""
    return {"status": "ok", "service": "ai-fastapi"}


@app.get("/ready")
async def readiness() -> dict[str, object]:
    if not translation_provider.is_ready:
        raise _not_ready_http_exception()
    payload: dict[str, object] = {
        "status": "ready",
        "service": "ai-fastapi",
        "translation": True,
    }
    if isinstance(translation_provider, IndicTrans2Provider):
        payload["provider"] = translation_provider.status
    return payload


@app.post("/api/v1/translation", response_model=TranslationResponse)
async def translate(request: TranslationRequest) -> TranslationResponse:
    if not translation_provider.is_ready:
        raise _not_ready_http_exception()
    try:
        return await translation_provider.translate(request)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("translation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "translation_inference_failed",
                "message": "The translation model could not complete the request.",
                "detail": type(error).__name__,
            },
        ) from error