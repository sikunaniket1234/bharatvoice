# BharatVoice task tracker

Status key: `[x]` complete, `[~]` in progress, `[ ]` not started, `[blocked]` waiting on an external decision or machine.

## Laptop — foundation

- [x] Establish repository layout and reproducible local development instructions.
- [x] Implement Phase 1 translation request/response contracts and reject unsupported language pairs.
- [x] Add FastAPI health/readiness endpoints and a replaceable `TranslationProvider` boundary.
- [x] Add NestJS gateway validation and forwarding to FastAPI.
- [x] Add API contract/unit tests; a missing model returns an explicit not-ready error, never fake a translation.
- [x] Migrate the prototype's main language tools into an Angular PWA and connect translation/conversation flows to NestJS.
- [x] Add local Docker Compose services for Angular/Nginx, NestJS, and FastAPI with loopback-only web/API ports.
- [x] Add local environment examples with safe non-secret defaults; keep actual secrets/model paths untracked.
- [x] Review, commit, and push the laptop foundation to the configured GitHub remote.
- [x] Complete the Angular PWA and local Docker Compose implementation; validate browser-to-gateway-to-AI behavior.
- [x] Commit and push the completed laptop implementation so the desktop can pull it.
- [ ] Review and resolve remaining frontend build/test toolchain advisories (runtime production dependency audit is clean).
- [x] Fix the NestJS/Jest type collision where hoisted `@types/jasmine` shadowed Jest's `expect` and broke `api:test`.

## Desktop — AI baseline (after laptop push)

- [x] Pull the agreed branch and confirm the repository instructions match the desktop OS.
- [x] Record OS, driver, CUDA/container support, free disk, RAM and available VRAM before installing AI dependencies.
- [x] Re-run the full laptop baseline on the desktop (API build/tests, Angular tests, FastAPI pytest, Compose stack, 503 not-ready path).
- [ ] Verify GPU-in-Docker passthrough: Docker Desktop's WSL2 backend exposes the GTX 1650 Super to Linux containers via `--gpus all`. No NVIDIA Container Toolkit installation is required on this Windows host.
- [x] Add a GPU device reservation to the `ai` Compose service only; gateway and web verified to have none.
- [~] Obtain Hugging Face access to the gated `indictrans2-en-indic-dist-200M` and `indictrans2-indic-en-dist-200M` checkpoints (account + accepted conditions + `HF_TOKEN`). External step; code is built and waiting on it.
- [x] Add `requirements-ml.txt` with `torch`, `transformers<5.0.0`, `IndicTransToolkit`, `sentencepiece`, `sacremoses`, `accelerate`, `huggingface_hub` and `sacrebleu`, as an opt-in Docker build argument.
- [x] Implement the environment-driven settings module, the single-resident-model lifecycle manager, and the real IndicTrans2 provider with sentence-aware chunking.
- [ ] Install the ML extras on this desktop and run the first real translation.
- [ ] Benchmark en->or: cold start, warm latency, RAM/VRAM; record in DESKTOP.md.
- [ ] Add or->en and verify en<->hi via indictrans2-indic-en-dist-200M.
- [x] Add a controlled bilingual evaluation set with the name/location/date/code-mixed tags the technical docs require, plus a benchmark runner recording BLEU/chrF, latency, VRAM and license.
- [ ] Human-review the Odia references and metrics before treating any score as a quality verdict; replace or supplement the smoke set with FLORES-200 devtest or IN22.
- [x] Keep model files out of Git and load/unload models rather than keeping every model resident on the 4 GB GPU.

## Later Phase 1

- [ ] Add PostgreSQL and Redis for application persistence, rate limits and job/session support.
- [ ] Add Gemma only after the direct IndicTrans2 baseline; schema-validate allow-listed normalization/routing output.
- [ ] Add IndicConformer ASR and Indic-TTS behind independent provider interfaces.
- [ ] Complete speech translation, transliteration beta and turn-based conversation.
- [ ] Add authentication, upload validation, retention/cleanup policy, backups, monitoring and security review before any pilot.
- [ ] Create private pilot deployment with Cloudflare Tunnel only after an explicit domain/account decision; never expose DB/Redis or forward router ports.

## Phase 2 (not current scope)

- [ ] Direct Odia ↔ Hindi translation, streaming conversation, long-form audio, document/image translation, more languages, offline inference and developer API/SDK.
