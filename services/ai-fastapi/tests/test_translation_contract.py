from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import FLORES_CODES, Settings
from app.providers.indictrans2 import chunk_text
from app.schemas import TranslationResponse

client = TestClient(main.app)


class _NotReadyProvider:
    is_ready = False

    async def translate(self, request):  # pragma: no cover - never reached
        raise AssertionError("translate must not run while the provider is not ready")


class _FakeProvider:
    is_ready = True

    async def translate(self, request):
        return TranslationResponse(
            translated_text="ନମସ୍କାର",
            source_language=request.source_language,
            target_language=request.target_language,
            model_name="IndicTrans2",
            model_version="test-checkpoint",
        )


@pytest.fixture
def provider(monkeypatch):
    def _install(instance):
        monkeypatch.setattr(main, "translation_provider", instance)
        return instance

    return _install


def test_health_is_live_without_loading_models() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-fastapi"}


def test_supported_pair_is_explicitly_not_ready_without_model(provider) -> None:
    provider(_NotReadyProvider())

    response = client.post(
        "/api/v1/translation",
        json={"text": "Hello", "source_language": "en", "target_language": "or"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "translation_provider_not_ready"


def test_readiness_is_503_while_provider_is_not_configured(provider) -> None:
    provider(_NotReadyProvider())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "translation_provider_not_ready"


def test_odia_to_hindi_is_rejected_in_phase_one() -> None:
    response = client.post(
        "/api/v1/translation",
        json={"text": "ନମସ୍କାର", "source_language": "or", "target_language": "hi"},
    )

    assert response.status_code == 422


def test_empty_text_is_rejected() -> None:
    response = client.post(
        "/api/v1/translation",
        json={"text": "   ", "source_language": "en", "target_language": "hi"},
    )

    assert response.status_code == 422


def test_same_language_pair_is_rejected() -> None:
    response = client.post(
        "/api/v1/translation",
        json={"text": "Hello", "source_language": "en", "target_language": "en"},
    )

    assert response.status_code == 422


def test_response_contract_is_served_when_a_provider_is_ready(provider) -> None:
    provider(_FakeProvider())

    response = client.post(
        "/api/v1/translation",
        json={"text": "Hello", "source_language": "en", "target_language": "or"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "translated_text": "ନମସ୍କାର",
        "source_language": "en",
        "target_language": "or",
        "model_name": "IndicTrans2",
        "model_version": "test-checkpoint",
    }


def test_inference_failure_surfaces_as_502(provider) -> None:
    class _BrokenProvider:
        is_ready = True

        async def translate(self, request):
            raise RuntimeError("checkpoint missing")

    provider(_BrokenProvider())

    response = client.post(
        "/api/v1/translation",
        json={"text": "Hello", "source_language": "en", "target_language": "or"},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "translation_inference_failed"


def test_flores_codes_cover_the_phase_1_languages() -> None:
    assert FLORES_CODES == {"en": "eng_Latn", "or": "ory_Orya", "hi": "hin_Deva"}


def test_flores_codes_match_the_checkpoint_language_tags() -> None:
    """Each checkpoint asserts its target tag against its own LANGUAGE_TAGS.

    Odia is ory_Orya, not ory_Deva. Getting this wrong produces an
    AssertionError deep inside the tokenizer's _src_tokenize, which surfaced as
    a 502 rather than a clear configuration error, so the exact strings are
    pinned here.
    """
    assert FLORES_CODES["or"] == "ory_Orya"
    assert FLORES_CODES["hi"] == "hin_Deva"
    assert FLORES_CODES["en"] == "eng_Latn"


def test_direction_selects_the_matching_checkpoint() -> None:
    settings = Settings(
        en_indic_model="en-indic",
        indic_en_model="indic-en",
        device="cpu",
        dtype="float32",
        max_input_tokens=512,
        max_new_tokens=512,
        num_beams=5,
        batch_size=8,
        eager_load=False,
        keep_resident=True,
        hf_cache_dir=None,
        hf_token=None,
        trust_remote_code=True,
    )

    assert settings.model_for("en") == "en-indic"
    assert settings.model_for("or") == "indic-en"
    assert settings.model_for("hi") == "indic-en"


def test_text_is_chunked_on_sentence_boundaries_including_danda() -> None:
    chunks = chunk_text("Hello there. ନମସ୍କାର। ଧନ୍ୟବାଦ।", max_chars=20)

    assert len(chunks) > 1
    assert " ".join(chunks) == "Hello there. ନମସ୍କାର। ଧନ୍ୟବାଦ।"


def test_chunking_never_drops_text() -> None:
    text = "This is a long English sentence. " * 40

    joined = " ".join(chunk_text(text, max_chars=200))

    assert joined == " ".join(chunk_text(text, max_chars=100_000))