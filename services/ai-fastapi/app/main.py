from fastapi import FastAPI, HTTPException, status

from app.providers.base import TranslationProvider
from app.providers.indictrans2 import IndicTrans2Provider
from app.schemas import TranslationRequest, TranslationResponse

app = FastAPI(
    title="BharatVoice AI Service",
    version="0.1.0",
    description="Private AI inference API; provider weights are configured separately.",
)
translation_provider: TranslationProvider = IndicTrans2Provider()


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check; it does not imply that model weights are loaded."""
    return {"status": "ok", "service": "ai-fastapi"}


@app.get("/ready")
async def readiness() -> dict[str, str | bool]:
    if not translation_provider.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "translation_provider_not_ready",
                "message": "The IndicTrans2 provider is not configured on this machine.",
            },
        )
    return {"status": "ready", "service": "ai-fastapi", "translation": True}


@app.post("/api/v1/translation", response_model=TranslationResponse)
async def translate(request: TranslationRequest) -> TranslationResponse:
    if not translation_provider.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "translation_provider_not_ready",
                "message": "Translation is unavailable until an IndicTrans2 model is configured.",
            },
        )
    return await translation_provider.translate(request)
