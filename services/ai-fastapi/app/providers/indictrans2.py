"""IndicTrans2 translation provider.

IndicTrans2 is the authoritative Phase 1 translation model. This provider owns
the preprocessing, generation and postprocessing described by the AI4Bharat
model cards, and delegates checkpoint lifecycle to `ModelManager` so that only
one model occupies the 4 GB GPU at a time.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from app.config import MODEL_LICENSES, FLORES_CODES, Settings, get_settings
from app.model_manager import ModelManager, get_manager
from app.providers.base import TranslationProvider
from app.schemas import TranslationRequest, TranslationResponse

logger = logging.getLogger(__name__)

MODEL_FAMILY = "IndicTrans2"

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।॥\n])\s+")
MAX_CHUNK_CHARS = 1200


def split_sentences(text: str) -> list[str]:
    """Split on sentence terminators, including Devanagari and Odia danda."""
    parts = [part.strip() for part in SENTENCE_BOUNDARY.split(text.strip())]
    return [part for part in parts if part]


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Group sentences into chunks so long input stays inside the model's window."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for sentence in split_sentences(text) or [text.strip()]:
        if current and length + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current))
            current, length = [], 0
        current.append(sentence)
        length += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks or [text.strip()]


class IndicTrans2Provider(TranslationProvider):
    """IndicTrans2 distilled-200M provider for the four Phase 1 directions."""

    def __init__(
        self,
        settings: Settings | None = None,
        manager: ModelManager | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._manager = manager or get_manager()
        self._failure: str | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def manager(self) -> ModelManager:
        return self._manager

    @property
    def is_ready(self) -> bool:
        """Readiness requires both a usable device and a loadable checkpoint."""
        if self._failure is not None:
            return False
        if not self._settings.is_torch_available():
            return False
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import IndicTransToolkit  # noqa: F401
        except ImportError:
            return False
        return True

    @property
    def status(self) -> dict[str, object]:
        settings = self._settings
        return {
            "ready": self.is_ready,
            "reason": self._failure
            or (
                None
                if self.is_ready
                else "Machine-learning extras are not installed for the configured device."
            ),
            "device": settings.device,
            "dtype": settings.dtype,
            "checkpoints": {
                "en_indic": settings.en_indic_model,
                "indic_en": settings.indic_en_model,
            },
            "licenses": {
                model_id: MODEL_LICENSES.get(model_id, "unknown")
                for model_id in settings.model_ids
            },
            "resident_model": self._manager.resident_model_id,
            "stats": self._manager.stats.as_dict(),
        }

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        if not self.is_ready:
            raise RuntimeError("IndicTrans2 runtime is not configured on this host.")

        model_id = self._settings.model_for(request.source_language)
        processor, tokenizer, model = await self._manager.acquire(model_id)
        source_code = FLORES_CODES[request.source_language]
        target_code = FLORES_CODES[request.target_language]

        chunks = chunk_text(request.text)
        loop = asyncio.get_running_loop()
        started = time.perf_counter()
        try:
            translated = await loop.run_in_executor(
                None,
                self._run_inference,
                processor,
                tokenizer,
                model,
                chunks,
                source_code,
                target_code,
            )
        finally:
            await self._manager.release()

        elapsed = time.perf_counter() - started
        self._manager.stats.last_inference_seconds = elapsed
        self._manager.stats.inference_count += 1

        logger.info(
            "translated %d char(s) %s->%s with %s in %.2fs",
            len(request.text),
            request.source_language,
            request.target_language,
            model_id,
            elapsed,
        )

        return TranslationResponse(
            translated_text=" ".join(part for part in translated if part).strip(),
            source_language=request.source_language,
            target_language=request.target_language,
            model_name=MODEL_FAMILY,
            model_version=model_id,
        )

    def _run_inference(
        self,
        processor,
        tokenizer,
        model,
        chunks: list[str],
        source_code: str,
        target_code: str,
    ) -> list[str]:
        import torch

        settings = self._settings
        results: list[str] = []
        for start in range(0, len(chunks), settings.batch_size):
            batch_chunks = chunks[start : start + settings.batch_size]
            processed = processor.preprocess_batch(
                batch_chunks,
                src_lang=source_code,
                tgt_lang=target_code,
            )
            inputs = tokenizer(
                processed,
                truncation=True,
                max_length=settings.max_input_tokens,
                padding="longest",
                return_tensors="pt",
                return_attention_mask=True,
            ).to(model.device)

            with torch.no_grad():
                generated = model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=settings.max_new_tokens,
                    num_beams=settings.num_beams,
                    num_return_sequences=1,
                )

            decoded = tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
            results.extend(processor.postprocess_batch(decoded, lang=target_code))
        return results