# Architecture notes

## Phase 1 boundary

Public translation pairs are `en → or`, `or → en`, `en → hi`, and `hi → en`. Reject all other pairs, including `or ↔ hi`. Use English-to-Indic and Indic-to-English IndicTrans2 distilled 200M checkpoints. IndicTrans2 is the translation authority; Gemma, when later introduced, is limited to schema-validated language intelligence, normalization and routing.

## Request path

`Angular PWA → NestJS API → FastAPI AI service → validated provider → response`

NestJS owns app-level request validation, auth, business logic and later history/rate limits. FastAPI owns model schemas, provider selection and inference. Keep providers replaceable and model frameworks out of the UI/API gateway.

## Laptop-first implementation boundary

The laptop can run contract tests and service development. The FastAPI contract should expose health and translation endpoints without downloading a model at import/startup. If no IndicTrans2 provider is configured, translation returns an explicit service-unavailable response. No dictionary/sample provider may masquerade as translation.

## Inference layer on the desktop

`app/config.py` reads model identifiers, device, dtype, beam width, batch size and Hugging Face token from the environment and imports nothing beyond the standard library. `app/model_manager.py` owns checkpoint lifecycle. `app/providers/indictrans2.py` owns preprocessing, generation and postprocessing.

Three constraints shape this layer:

1. **Heavy imports are always deferred.** `app.main` must import on a machine with no PyTorch, so that the contract tests and health endpoints still work. Nothing in the import path pulls in `torch`, `transformers` or `IndicTransToolkit`.
2. **One resident model.** The GPU has 4 GB of VRAM and the deployment plan forbids keeping every model resident. The manager keeps at most one IndicTrans2 checkpoint loaded, serialises inference behind a single lock, and releases the checkpoint when `AI_KEEP_MODEL_RESIDENT=false`.
3. **Direction selects the checkpoint.** IndicTrans2 ships one checkpoint per direction, not one per pair. English source uses `indictrans2-en-indic-dist-200M`; Odia or Hindi source uses `indictrans2-indic-en-dist-200M`.

Input is split on sentence boundaries, including the Devanagari and Odia danda, so the 5,000-character API contract does not silently truncate at the model's generation limit. `flash_attention_2` is deliberately not enabled because it has no supported Windows build.

## GPU isolation

Only the `ai` service carries a GPU device reservation in Compose. The gateway, web tier, PostgreSQL and Redis run on CPU and RAM. Model weights live on a named volume, never in the repository or an image layer. The machine-learning extras are an opt-in build argument so a default build stays small and the service reports itself not-ready.

## Later services

PostgreSQL, Redis, object storage, authentication, asynchronous jobs, monitoring and deployment ingress are added only as their requirements arrive. The local stack defaults to private/localhost access. Cloudflare Tunnel is a later opt-in private-pilot ingress, never a substitute for authentication or application security.
