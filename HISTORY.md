# Project history

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
