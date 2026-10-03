# Architecture notes

## Phase 1 boundary

Public translation pairs are `en → or`, `or → en`, `en → hi`, and `hi → en`. Reject all other pairs, including `or ↔ hi`. Use English-to-Indic and Indic-to-English IndicTrans2 distilled 200M checkpoints. IndicTrans2 is the translation authority; Gemma, when later introduced, is limited to schema-validated language intelligence, normalization and routing.

## Request path

`Angular PWA → NestJS API → FastAPI AI service → validated provider → response`

NestJS owns app-level request validation, auth, business logic and later history/rate limits. FastAPI owns model schemas, provider selection and inference. Keep providers replaceable and model frameworks out of the UI/API gateway.

## Laptop-first implementation boundary

The laptop can run contract tests and service development. The FastAPI contract should expose health and translation endpoints without downloading a model at import/startup. If no IndicTrans2 provider is configured, translation returns an explicit service-unavailable response. No dictionary/sample provider may masquerade as translation.

## Later services

PostgreSQL, Redis, object storage, authentication, asynchronous jobs, monitoring and deployment ingress are added only as their requirements arrive. The local stack defaults to private/localhost access. Cloudflare Tunnel is a later opt-in private-pilot ingress, never a substitute for authentication or application security.
