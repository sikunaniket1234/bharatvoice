# Initial API contract (v0.1)

## Translation

`POST /api/v1/translation`

Request:

```json
{
  "text": "Hello",
  "source_language": "en",
  "target_language": "or"
}
```

The request is limited to 1–5,000 characters. Supported codes are `en`, `or`, and `hi`; only `en → or`, `or → en`, `en → hi`, and `hi → en` are permitted. Odia ↔ Hindi, same-language requests, blank input, and unknown fields are rejected.

Successful response (once a model provider is installed):

```json
{
  "translated_text": "…",
  "source_language": "en",
  "target_language": "or",
  "model_name": "IndicTrans2",
  "model_version": "configured-checkpoint-version"
}
```

If no real IndicTrans2 model is configured, the AI service returns HTTP 503 with `code: translation_provider_not_ready`. The NestJS gateway forwards that not-ready state. It must not use prototype phrases as a substitute for a model result.

## Health

- `GET /api/v1/health` on NestJS reports gateway liveness.
- `GET /health` on FastAPI reports AI process liveness only.
- `GET /ready` on FastAPI reports provider readiness and returns 503 until a model is configured.

Liveness is not readiness. These local endpoints are not an authentication or public-ingress design. Add other PRD endpoints only when their providers/contracts are implemented and tested.
