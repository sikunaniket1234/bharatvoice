from typing import Protocol

from app.schemas import TranslationRequest, TranslationResponse


class TranslationProvider(Protocol):
    """Replaceable interface for the authoritative translation model."""

    @property
    def is_ready(self) -> bool:
        """Whether the provider can serve requests without loading failure."""

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate one validated Phase 1 request."""
