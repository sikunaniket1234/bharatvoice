"""Model lifecycle management for a small-VRAM GPU.

The GTX 1650 Super has 4 GB of VRAM and the deployment plan explicitly forbids
keeping every model resident. This manager therefore keeps at most one
IndicTrans2 checkpoint loaded at a time, serialises inference behind a single
lock, and can evict the resident model so the GPU is released between phases.

Heavy imports happen inside methods, not at module scope, so importing this
module never requires torch.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, get_settings, torch_dtype

logger = logging.getLogger(__name__)


@dataclass
class ModelStats:
    """Observability for the readiness endpoint and later benchmarking."""

    model_id: str | None = None
    device: str | None = None
    dtype: str | None = None
    load_seconds: float | None = None
    last_inference_seconds: float | None = None
    inference_count: int = 0
    evictions: int = 0
    allocated_vram_bytes: int | None = None
    reserved_vram_bytes: int | None = None
    loaded_at: float | None = None
    licenses: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "device": self.device,
            "dtype": self.dtype,
            "load_seconds": round(self.load_seconds, 3) if self.load_seconds else None,
            "last_inference_seconds": (
                round(self.last_inference_seconds, 3)
                if self.last_inference_seconds
                else None
            ),
            "inference_count": self.inference_count,
            "evictions": self.evictions,
            "allocated_vram_bytes": self.allocated_vram_bytes,
            "reserved_vram_bytes": self.reserved_vram_bytes,
        }


class ModelManager:
    """Owns the single resident IndicTrans2 checkpoint."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._lock = asyncio.Lock()
        self._load_lock = threading.Lock()
        self._model: Any = None
        self._tokenizer: Any = None
        self._processor: Any = None
        self._resident_model_id: str | None = None
        self.stats = ModelStats()

    @property
    def resident_model_id(self) -> str | None:
        return self._resident_model_id

    def is_loaded(self, model_id: str | None = None) -> bool:
        if self._model is None:
            return False
        if model_id is None:
            return True
        return self._resident_model_id == model_id

    def _vram_snapshot(self) -> tuple[int | None, int | None]:
        if self._settings.device == "cpu":
            return None, None
        try:
            import torch
        except ImportError:
            return None, None
        if not torch.cuda.is_available():
            return None, None
        return (
            int(torch.cuda.memory_allocated()),
            int(torch.cuda.memory_reserved()),
        )

    def vram_snapshot(self) -> tuple[int | None, int | None]:
        """Currently allocated and reserved VRAM in bytes, for benchmarking."""
        return self._vram_snapshot()

    @property
    def settings(self) -> Settings:
        return self._settings

    def _load(self, model_id: str) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        from IndicTransToolkit.processor import IndicProcessor

        settings = self._settings
        if settings.hf_token:
            from huggingface_hub import login

            login(token=settings.hf_token, add_to_git_credential=False)

        logger.info("loading checkpoint %s on %s (%s)", model_id, settings.device, settings.dtype)
        started = time.perf_counter()

        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=settings.trust_remote_code,
            token=settings.hf_token,
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id,
            trust_remote_code=settings.trust_remote_code,
            token=settings.hf_token,
            torch_dtype=torch_dtype(settings.dtype),
        )

        if settings.device == "cuda" and torch.cuda.is_available():
            model = model.to("cuda")
        elif settings.device != "cpu":
            raise RuntimeError(f"AI_DEVICE={settings.device!r} is not available on this host.")

        model.eval()
        processor = IndicProcessor(inference=True)
        elapsed = time.perf_counter() - started

        self._model = model
        self._tokenizer = tokenizer
        self._processor = processor
        self._resident_model_id = model_id

        allocated, reserved = self._vram_snapshot()
        self.stats = ModelStats(
            model_id=model_id,
            device=settings.device,
            dtype=settings.dtype,
            load_seconds=elapsed,
            allocated_vram_bytes=allocated,
            reserved_vram_bytes=reserved,
            loaded_at=time.time(),
            licenses=self._licenses(),
        )
        logger.info("checkpoint %s ready in %.2fs", model_id, elapsed)

    def _licenses(self) -> dict[str, str]:
        from app.config import MODEL_LICENSES

        return {
            model_id: MODEL_LICENSES.get(model_id, "unknown")
            for model_id in self._settings.model_ids
        }

    def _ensure_loaded(self, model_id: str) -> None:
        if self.is_loaded(model_id):
            return
        if self._model is not None:
            self.unload()
        self._load(model_id)

    def unload(self) -> None:
        """Release the resident checkpoint and hand VRAM back to the driver."""
        with self._load_lock:
            if self._model is None and self._tokenizer is None:
                return
            logger.info("unloading checkpoint %s", self._resident_model_id)
            self._model = None
            self._tokenizer = None
            self._processor = None
            self._resident_model_id = None
            self.stats.evictions += 1
            self.stats.allocated_vram_bytes = None
            self.stats.reserved_vram_bytes = None
            gc.collect()
            if self._settings.device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass

    def warm_up(self) -> None:
        """Preload a checkpoint so the first user request is not a cold start."""
        if not self._settings.eager_load:
            return
        try:
            self._load(self._settings.en_indic_model)
        except Exception:
            logger.exception("eager load failed; the service will retry lazily per request")

    async def acquire(self, model_id: str) -> Any:
        """Return the processor/tokenizer/model trio for a checkpoint, loading on demand."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._ensure_loaded, model_id)
            return self._processor, self._tokenizer, self._model

    async def release(self) -> None:
        async with self._lock:
            if not self._settings.keep_resident:
                await asyncio.get_running_loop().run_in_executor(None, self.unload)


_manager: ModelManager | None = None


def get_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager