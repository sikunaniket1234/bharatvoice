from app.providers.base import TranslationProvider
from app.schemas import TranslationRequest, TranslationResponse


class IndicTrans2Provider(TranslationProvider):
    """IndicTrans2 provider boundary; model loading is implemented on the desktop milestone."""

    @property
    def is_ready(self) -> bool:
        # Do not download or load large checkpoints during laptop API startup.
        return False

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        raise RuntimeError("IndicTrans2 model weights and runtime are not configured.")
