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

`model_name` is the model family (`IndicTrans2`) and `model_version` is the
checkpoint identifier that actually served the request, for example
`ai4bharat/indictrans2-en-indic-dist-200M`. Two checkpoints exist, one per
direction, not one per language pair: English source uses the En-Indic model,
and Odia or Hindi source uses the Indic-En model.

If no real IndicTrans2 model is configured, the AI service returns HTTP 503 with `code: translation_provider_not_ready`. The NestJS gateway forwards that not-ready state. It must not use prototype phrases as a substitute for a model result.

If a provider is ready but inference itself fails, the AI service returns HTTP
502 with `code: translation_inference_failed` rather than inventing output.

## Health

- `GET /api/v1/health` on NestJS reports gateway liveness.
- `GET /health` on FastAPI reports AI process liveness only.
- `GET /ready` on FastAPI reports provider readiness and returns 503 until a model is configured.

Liveness is not readiness. These local endpoints are not an authentication or public-ingress design. Add other PRD endpoints only when their providers/contracts are implemented and tested.

Both the 503 and the ready responses carry a `provider` object describing the
AI service's actual state, so an operator can tell "no weights configured" from
"weights configured but not loaded yet":

```json
{
  "ready": false,
  "reason": "Machine-learning extras are not installed for the configured device.",
  "device": "cpu",
  "dtype": "float16",
  "checkpoints": {
    "en_indic": "ai4bharat/indictrans2-en-indic-dist-200M",
    "indic_en": "ai4bharat/indictrans2-indic-en-dist-200M"
  },
  "licenses": {
    "ai4bharat/indictrans2-en-indic-dist-200M": "MIT",
    "ai4bharat/indictrans2-indic-en-dist-200M": "MIT"
  },
  "resident_model": null,
  "stats": { "…": "load and inference counters" }
}
```
