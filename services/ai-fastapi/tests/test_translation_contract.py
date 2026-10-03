from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_live_without_loading_models() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-fastapi"}


def test_supported_pair_is_explicitly_not_ready_without_model() -> None:
    response = client.post(
        "/api/v1/translation",
        json={"text": "Hello", "source_language": "en", "target_language": "or"},
    )

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
