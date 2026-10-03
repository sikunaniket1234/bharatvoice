"""Environment-driven configuration for the AI service.

This module deliberately imports nothing heavier than the standard library so
that the API contract, health endpoints and unit tests keep working on a
machine where the machine-learning extras are not installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas import LanguageCode

FLORES_CODES: dict[LanguageCode, str] = {
    "en": "eng_Latn",
    "or": "ory_Deva",
    "hi": "hin_Deva",
}

DEFAULT_EN_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
DEFAULT_INDIC_EN_MODEL = "ai4bharat/indictrans2-indic-en-dist-200M"

MODEL_LICENSES: dict[str, str] = {
    "ai4bharat/indictrans2-en-indic-dist-200M": "MIT",
    "ai4bharat/indictrans2-indic-en-dist-200M": "MIT",
}


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def _env_int(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, "true" if default else "false").lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime settings for model loading and inference."""

    en_indic_model: str
    indic_en_model: str
    device: str
    dtype: str
    max_input_tokens: int
    max_new_tokens: int
    num_beams: int
    batch_size: int
    eager_load: bool
    keep_resident: bool
    hf_cache_dir: Path | None
    hf_token: str | None
    trust_remote_code: bool

    @property
    def model_ids(self) -> tuple[str, str]:
        return (self.en_indic_model, self.indic_en_model)

    def model_for(self, source_language: LanguageCode) -> str:
        """IndicTrans2 ships one checkpoint per direction, not one per pair."""
        if source_language == "en":
            return self.en_indic_model
        return self.indic_en_model

    def is_torch_available(self) -> bool:
        if self.device == "cpu":
            return True
        try:
            import torch
        except ImportError:
            return False
        return torch.cuda.is_available()


def _resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch
    except ImportError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def resolve_token() -> str | None:
    """Find a Hugging Face token without ever logging it.

    Prefers the HF_TOKEN environment variable so a secret can stay out of the
    Hugging Face cache, but falls back to `hf auth login`, which is the
    convenient path for an interactive developer.
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token and token.strip():
        return token.strip()
    try:
        from huggingface_hub import get_token
    except ImportError:
        return None
    try:
        return get_token()
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cache_dir = _env("HF_HOME", "")
    return Settings(
        en_indic_model=_env("AI_TRANSLATION_MODEL_EN_INDIC", DEFAULT_EN_INDIC_MODEL),
        indic_en_model=_env("AI_TRANSLATION_MODEL_INDIC_EN", DEFAULT_INDIC_EN_MODEL),
        device=_resolve_device(_env("AI_DEVICE", "auto")),
        dtype=_env("AI_DTYPE", "float16"),
        max_input_tokens=_env_int("AI_MAX_INPUT_TOKENS", 512),
        max_new_tokens=_env_int("AI_MAX_NEW_TOKENS", 512),
        num_beams=_env_int("AI_NUM_BEAMS", 5),
        batch_size=_env_int("AI_BATCH_SIZE", 8),
        eager_load=_env_bool("AI_EAGER_LOAD", False),
        keep_resident=_env_bool("AI_KEEP_MODEL_RESIDENT", True),
        hf_cache_dir=Path(cache_dir) if cache_dir else None,
        hf_token=resolve_token(),
        trust_remote_code=_env_bool("AI_TRUST_REMOTE_CODE", True),
    )


def torch_dtype(name: str):
    """Map a configured dtype name onto a torch dtype without importing torch here."""
    import torch

    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }.get(name, torch.float32)