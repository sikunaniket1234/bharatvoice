# Project history

## 2026-10-03 — Real IndicTrans2 inference on the GTX 1650 Super

Authenticated the gated Hugging Face checkpoints and got genuine GPU translation working end to end for the first time. Both checkpoints report `gated: "auto"` and now resolve for the configured token; the AI service reports `ready: true` and the browser-facing Translate tab is live.

Running the model for real surfaced four defects that unit tests and import checks could not have caught. All four are fixed and the reasons are recorded in the code so they do not regress:

- **Wrong FLORES code for Odia.** `config.py` mapped `or` to `ory_Deva`. Neither checkpoint accepts that tag; their own `LANGUAGE_TAGS` requires `ory_Orya`. The failure surfaced as an HTTP 502 with an `AssertionError` buried inside the tokenizer's `_src_tokenize`, not as a configuration error. Corrected and pinned in the test suite.
- **`transformers` was too new for the checkpoint's bundled code.** The models are `trust_remote_code`, and `modeling_indictrans.py` computes `past_key_values[0][0].shape[2] if past_key_values is not None else 0`. That breaks on the `Cache` object introduced later in the 4.x line, where a fresh cache returns `None` for index 0: `AttributeError: 'NoneType' object has no attribute 'shape'`. Verified empirically that 4.57.6 fails and 4.46.3 generates, then pinned `transformers>=4.46,<4.47` with the evidence recorded in `requirements-ml.txt`.
- **The image had no C compiler.** `python:3.12-slim` plus torch means Triton's first-use kernel build fails with `Failed to find C compiler`, which the gateway reported as an opaque 502. Added `build-essential` to the Dockerfile.
- **`sacrebleu` 2.6.0 removed `BLEUScore.get_signature()`,** which crashed the benchmark *after* all 25 rows had translated. Rewritten to read the signature from the metric class, version-tolerantly.

Also set `AI_EAGER_LOAD=true` in `.env`. The gateway's `AbortSignal.timeout(15_000)` cannot absorb a cold checkpoint load, so without eager loading the first request after every idle period reliably 503s. Kept `AI_INSTALL_ML=true` in the git-ignored `.env` so rebuilds stay inference-capable.

Measured on the GTX 1650 Super at fp16, via `scripts/benchmark_translation.py` over the 25-row controlled set:

| Direction | Rows | Cold load | Warm p50 | Warm p95 | VRAM | BLEU | chrF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| en→or | 12/12 | 2.196s | 0.453s | 0.718s | 413.2 MB | 12.49 | 55.89 |
| or→en | 13/13 | 44.087s | 0.365s | 0.453s | 413.2 MB | 71.78 | 78.40 |

Warm latency is roughly 0.4s and a single resident checkpoint costs 413 MB, so the 4 GB card has wide headroom and the PRD's sub-3-second target is met with margin. Through the full browser path (nginx → gateway → AI) a request returns in 4.3s including the HTTP hop, and switching direction costs about 5s for the checkpoint swap, which stays inside both the 15s gateway and 30s nginx timeouts.

The BLEU 12.49 for en→or is **not** a quality verdict and must not be read as one. It is 12 self-authored sentences, far too few for BLEU to mean anything; or→en scoring 71.78 against comparable references indicates the en→or references were less idiomatic rather than the output being worse. A defensible number needs the official FLORES-200 devtest set, which is recorded as follow-up work in `eval/README.md`.

- Restricted speech-to-text to English and Odia via a `SPEECH_INPUT_LANGUAGES` allowlist. The microphone is disabled with an explanatory tooltip when Hindi is selected, and `toggleListening` re-checks so the restriction cannot be bypassed. Hindi remains fully available for typing, text-to-speech and transliteration.
- Added same-language dictation: English→English and Odia→Odia now transcribe only and never reach the model, because `en:en` and `or:or` are not valid IndicTrans2 pairs and round-tripping correct text through the model could only corrupt it. `constrainPair` permits these while still rejecting Hindi→Hindi and the direct Odia↔Hindi pair that IndicTrans2 cannot serve without an English pivot. Applied to both the Translate tab and the conversation turn handler.
- Added a "Write it in" target selector to the Speech-to-text tab so that tab alone can produce all four supported pairs instead of hardcoding the opposite language.
- Fixed a mic feedback bug: recording state was `speechListening = target === 'speech'`, so dictating in the Translate or Conversation tab gave no visual indication that recording was active. Now tracked per target via `listeningTarget`.
- Removed the false claim "Your words stay private on this device" from the Translate tab. Chrome and Edge stream microphone audio to Google's servers for recognition, so the sentence was untrue for the one feature a user would most assume was local. The status region now renders only when there is a real message, and the decorative star is conditional so no orphan glyph is left behind.
- Added the authorship notice to the footer: "© 2026 Aniket Nayak · All rights reserved" and "Designed and developed by Aniket Nayak". Used a `div` rather than a `span` so the existing `.footer > span:last-child` rule does not shrink it to 8px, and replaced the dev-facing "LOCAL PREVIEW · PHASE 1" label to keep the footer from crowding.
- Verified: FastAPI pytest 13/13; NestJS Jest 2/2; Angular tests 7/7 in Chrome 154; Angular production build clean. Translation confirmed end to end through nginx for both directions, and all four change markers confirmed present in the bundle actually served on port 4200 rather than only in source.

Known gaps carried forward: the Speech-to-text tab still cannot transcribe Hindi; `hi` is offered for typing and translation but was never benchmarked; the footer notice is the only authorship marker, as `package.json` carries no `author` or `license` field and the README has no ownership statement; and the transliteration tool remains a seven-word lookup table rather than IndicXlit.

## 2026-10-03 — Desktop AI inference layer (built, awaiting gated checkpoints)

Built the IndicTrans2 inference layer on the AI development desktop. No weights have been downloaded; the service still reports not-ready, which is the correct behaviour until Hugging Face access exists.

- Added `app/config.py`: environment-driven settings for checkpoint ids, device, dtype, beam width, batch size, token limits and `HF_TOKEN`. Imports only the standard library, so nothing heavy is pulled in at startup.
- Added `app/model_manager.py`: checkpoint lifecycle for a 4 GB card. Keeps at most one IndicTrans2 checkpoint resident, serialises inference behind a single asyncio lock, evicts before switching direction, optionally releases VRAM after each request, and tracks load time, latency and allocated/reserved VRAM.
- Implemented `app/providers/indictrans2.py` against the AI4Bharat model cards: `IndicProcessor` preprocess/postprocess, fp16 generation with beam search, direction-based checkpoint selection, and sentence-aware chunking that respects Devanagari and Odia danda so the 5,000-character API contract does not silently truncate.
- Recorded the model family and the checkpoint that actually served each request in `model_name` / `model_version`, and surfaced MIT license metadata on the readiness endpoint.
- Added `requirements-ml.txt` and made the ML extras an opt-in Docker build argument, so a default build stays small. Pinned `transformers<5.0.0` per the model-card warning about the removed translation pipeline, and deliberately did not enable `flash_attention_2` because it has no supported Windows build.
- Gave only the `ai` Compose service a GPU device reservation; confirmed by container inspect that the gateway and web services have none. Model weights go to a named volume, never the repository or an image layer.
- Added `eval/phase1_smoke.jsonl`, a 49-row controlled set covering all four directions with the name, location, date and code-mixed tags the technical documentation requires, including the PRD's own `ମୁଁ ଆଜି office ଯିବିନି।` example.
- Added `scripts/benchmark_translation.py`, which reports per-direction cold load, warm latency mean/p50/p95, VRAM, RAM, BLEU, chrF, checkpoint id and license, and exits non-zero on any error. `eval/README.md` states plainly that the references are self-authored and therefore usable only as a regression signal, not a quality verdict.
- Made the readiness response actionable: 503 and ready responses now include a `provider` object with the failure reason, device, configured checkpoints and licenses. Inference failures now surface as HTTP 502 `translation_inference_failed` instead of a bare error.
- Rewrote the FastAPI tests to be deterministic by injecting a fake provider, removing the previous dependency on PyTorch being absent. Added coverage for the response contract, the 502 path, FLORES code mapping, direction-to-checkpoint routing and chunking. 12/12 pass with no ML stack installed.
- Verified: FastAPI pytest 12/12; Compose stack rebuilds and serves web 200, gateway 200, AI `/ready` 503 with provider detail, gateway translation 503.

Still blocked on external Hugging Face access: both checkpoints report `gated: "auto"` and return HTTP 401 without a token.

## 2026-10-03 — Desktop first pull and baseline verification

- Cloned `origin/main` fresh on the AI development desktop at commit `bc82f1b` and read the repository docs plus all three supplied source documents.
- Confirmed the desktop is Hardware Profile B from the deployment plan: i5-11400, 15.87 GiB RAM, GTX 1650 Super with 4.00 GiB VRAM. Recorded the full measured environment table in [DESKTOP.md](DESKTOP.md), replacing the previous "pending inspection" status.
- The host OS is Windows 11 Pro `10.0.26200`, not Ubuntu Server 24.04 LTS. Recorded the seven environment deviations that affect inference, including absent `flash_attention_2`, PowerShell blocking `npm.ps1`, gated Hugging Face checkpoints, and the `transformers<5.0.0` pin requirement.
- Installed Python 3.12.10 to satisfy the documented `py -3.12` workflow; 3.14.7 and 3.10 were already present.
- Found and fixed a latent monorepo type-collision bug: `apps/api-nestjs/tsconfig.json` had no `types` restriction, so the Angular workspace's hoisted `@types/jasmine` shadowed Jest's `expect` and `npm run api:test` failed with `TS2339: Property 'rejects' does not exist`. Fixed with `"types": ["node", "jest"]`.
- Recorded the five npm install-script approvals (`@parcel/watcher`, `esbuild`, `lmdb`, `msgpackr-extract`, `unrs-resolver`) in `package.json` `allowScripts` so the Angular build is reproducible without a manual approval step.
- Verified the laptop baseline on the desktop: FastAPI pytest 4/4; NestJS build and Jest 2/2; Angular tests 3/3 in Chrome 154.
- Brought up the Docker Compose stack: web, gateway and AI containers all up with `ai` healthy. Web HTTP 200, gateway health HTTP 200, FastAPI `/health` HTTP 200 from inside the network, `/ready` HTTP 503 `translation_provider_not_ready`, and gateway translation HTTP 503. Confirmed FastAPI is not published to a host port.
- Confirmed `IndicTransToolkit` 1.1.1 is the real PyPI package required by the IndicTrans2 model cards, and that both 200M checkpoints are gated on Hugging Face. The AI baseline is now blocked on external Hugging Face access.
- No model weights were downloaded. Nothing has been committed or pushed yet.

## 2026-10-03 — Initial laptop review

- Reviewed the Phase 1 PRD, AI technical documentation, server/deployment documentation, and standalone HTML prototype.
- Confirmed Phase 1 translation scope is English ↔ Odia and English ↔ Hindi; Odia ↔ Hindi is Phase 2.
- Confirmed deployment split: laptop for UI/API development and browser/API testing; desktop with GTX 1650 Super 4 GB for AI inference/model evaluation. Laptop CPU inference is not the planned model benchmark environment.
- Checked local tool versions: Node.js 24.14.0, npm 11.11.1, Python 3.12.10, Docker CLI 29.3.1 and Docker Compose 5.1.1. Docker daemon readiness has not been verified.
- Added FastAPI translation contract/provider boundary and NestJS validation/proxy gateway. No model weights are loaded; requests return explicit not-ready until desktop inference is implemented.
- Validation passed: FastAPI pytest 4/4; NestJS build and Jest 2/2; npm audit 0 vulnerabilities.
- Initialized the local `main` branch and configured `origin` as `https://github.com/sikunaniket1234/bharatvoice.git`.
- Created and pushed the initial project commit `9b3ee623eee7c9b850bd64aeed52ed38ef26cc5c` (`chore: initial BharatVoice project foundation`) to `origin/main`.
- Initial work is being tracked in [TASKS.md](TASKS.md); machine handoff steps are in [LAPTOP.md](LAPTOP.md) and [DESKTOP.md](DESKTOP.md).

## 2026-10-03 — Laptop web implementation

- Added the Angular 20 responsive Odia-first PWA with translation, browser speech input/output, local-only history, conversation UI, transliteration preview, and light/dark themes.
- Connected translation and conversation requests to the NestJS endpoint; the backend's explicit model-not-ready status is shown without substituting samples.
- Added local dev proxy plus Docker Compose services for Angular/Nginx, NestJS, and FastAPI. Web/API host ports are loopback-only; FastAPI is private to the Compose network.
- Confirmed Docker Desktop is running (Linux containers). `docker compose up -d` started all three services; the web returns HTTP 200, API health returns HTTP 200, and translation returns the expected HTTP 503 until desktop IndicTrans2 is configured.
- Validation passed: Angular production build; Angular tests 3/3; NestJS build/tests 2/2; FastAPI tests 4/4; production dependency audit (`npm audit --omit=dev`) 0 vulnerabilities.
- Full npm audit reports remaining high-severity Angular CLI/legacy Karma development-tool advisories (including critical Piscina advisory); tracked separately and not present in the production dependency audit.
- Docker Compose web image was rebuilt after the final UI/privacy-copy changes; web/API/private-AI health smoke checks passed.
- Committed and pushed the completed laptop implementation as `93e04ded58612dd880336780f35a0030c6b9b13f` (`feat: add BharatVoice Angular PWA and Docker stack`) to `origin/main`.
