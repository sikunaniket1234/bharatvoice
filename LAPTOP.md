# Laptop development guide

## Role and constraints

Per the deployment plan, this Windows laptop (10th-gen i5, 12 GB RAM, no useful CUDA GPU) is the secondary development/client machine. Use it for Angular/NestJS/FastAPI code, browser work and API tests. CPU-only model experiments may be useful for wiring, but do not download/run the full speech/LLM stack here or treat laptop results as desktop performance benchmarks.

## Tool check recorded 2026-10-03

- Node.js: 24.14.0
- npm: 11.11.1
- Python: 3.12.10
- Docker CLI: 29.3.1
- Docker Compose: v5.1.1
- Git: installed (the `git status` check ran); this directory was not yet a Git repository.
- Docker daemon, desktop GPU, ports and browser microphone permissions have not been tested. The Python virtual environment and Node/Python dependencies are installed locally and ignored by Git.
- Checks passed: `npm run api:build`, `npm run api:test` (2 tests), `python -m pytest services/ai-fastapi` (4 tests), and `npm audit` (0 vulnerabilities).

## Local workflow

1. Keep the prototype available as a behavior/design reference until its Angular replacement is ready.
2. From the repository root, create a Python virtual environment and install the pinned lightweight dependencies:

	```powershell
	py -3.12 -m venv .venv
	.\.venv\Scripts\python.exe -m pip install -r services/ai-fastapi/requirements.txt
	.\.venv\Scripts\python.exe -m pytest services/ai-fastapi
	.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services/ai-fastapi --host 127.0.0.1 --port 8000
	```

	Run the test command before starting Uvicorn. Use a second terminal for the other service.
3. From the repository root, install and check the NestJS workspace:

	```powershell
	npm install
	npm run api:build
	npm run api:test
	npm run api:dev
	```

	The API listens on `127.0.0.1:3000`; the default AI service URL is `http://127.0.0.1:8000`. Copy `.env.example` to `.env` only if local overrides are required. The default translation result is HTTP 503 until a real model provider is configured.
4. Run the Angular development server when that app is scaffolded; point it to the local NestJS API through an environment-specific URL, not a production hostname.
5. Use sample/fixture data only when testing UI wiring. The API must report model-not-ready until a real translation provider is configured; do not silently return sample translations.
6. Do not add model weights, `.env` secrets, audio recordings, virtual environments, `node_modules`, build output or local databases to Git.
7. Do not expose services on the public Internet. Keep ports bound to localhost unless a deliberate private LAN test is needed; never expose PostgreSQL or Redis.

## Git handoff

The repository is initialized on `main` and `origin` points to `https://github.com/sikunaniket1234/bharatvoice.git`. After reviewing `git status`, push the initial commit so the desktop can pull it. Do not commit secrets or downloaded checkpoints. Record the pushed commit in [DESKTOP.md](DESKTOP.md).

## Laptop completion checklist

- [x] Verify Python venv creation and API tests.
- [x] Verify Node dependencies and NestJS tests/build.
- [ ] Build/migrate the Angular PWA and test it in a browser.
- [x] Confirm NestJS/FastAPI contracts and expected not-ready behavior (the Angular UI connection remains open work).
- [x] Review `.gitignore`, environment files and staged changes.
- [ ] Push the initial commit to origin; update [HISTORY.md](HISTORY.md) and [TASKS.md](TASKS.md) with its hash.
