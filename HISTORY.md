# Project history

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
