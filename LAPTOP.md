# Laptop development guide

## Role and constraints

Per the deployment plan, this Windows laptop (10th-gen i5, 12 GB RAM, no useful CUDA GPU) is the secondary development/client machine. Use it for Angular/NestJS/FastAPI code, browser work and API tests. CPU-only model experiments may be useful for wiring, but do not download/run the full speech/LLM stack here or treat laptop results as desktop performance benchmarks.

## Tool check recorded 2026-10-03

- Node.js: 24.14.0
- npm: 11.11.1
- Python: 3.12.10
- Docker CLI: 29.3.1
- Docker Compose: v5.1.1
- Git: installed; repository on `main` with configured `origin`.
- Docker Desktop is running with Linux containers. Services were launched and smoke-tested at the local ports below. Browser microphone recognition still depends on browser permissions and language support.
- Checks passed: Angular production build/tests (3 tests), NestJS build/tests (2 tests), FastAPI tests (4 tests), and `npm audit --omit=dev` (0 production dependency vulnerabilities). The full development dependency tree has outstanding Angular CLI/Karma advisories; see [TASKS.md](TASKS.md).

## Local workflow

1. Keep the prototype available as a behavior/design reference; the Angular PWA is now implemented alongside it.
2. From the repository root, install the pinned workspace dependencies and create the Python environment:

	```powershell
	npm ci
	py -3.12 -m venv .venv
	.\.venv\Scripts\python.exe -m pip install -r services/ai-fastapi/requirements.txt
	```

3. To run services directly on Windows instead of Docker, open separate terminals from the repository root:

	```powershell
	# Terminal 1 — FastAPI
	.\.venv\Scripts\python.exe -m pytest services\ai-fastapi
	.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services\ai-fastapi --host 127.0.0.1 --port 8000
	```

	```powershell
	# Terminal 2 — NestJS
	npm run api:build
	npm run api:test
	npm run api:dev
	```

	The API listens on `127.0.0.1:3000`; the default AI service URL is `http://127.0.0.1:8000`. NestJS loads the root `.env` if present. Translation returns HTTP 503 until a real model provider is configured.
4. In another terminal, run `npm run web:dev` and open `http://localhost:4200`. Angular's dev proxy forwards `/api` to NestJS on port 3000.
5. Use sample/fixture data only to test UI wiring. The API must report model-not-ready until a real provider is configured; it must not return sample phrases as translations.
6. Do not add model weights, `.env` secrets, audio recordings, virtual environments, `node_modules`, build output or local databases to Git.
7. Do not expose services on the public Internet. Keep ports bound to localhost unless a deliberate private LAN test is needed; never expose PostgreSQL or Redis.

## Docker Compose workflow

Docker Desktop was verified running with Linux containers. From the repository root:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f web api ai
```

Open the web application at `http://127.0.0.1:4200`. Nginx serves the production Angular PWA and proxies `/api/` internally to NestJS. The API is also reachable at `http://127.0.0.1:3000`. FastAPI is intentionally not published to the host; it is available only to containers on the private Compose network. Rebuild the `web` service after frontend-source changes. Stop the stack with `docker compose down` (named Node dependency volumes are retained).

Do not publish the Docker ports on the LAN or Internet for this development setup. The translation response remains HTTP 503 until the desktop model provider is implemented.

## Git handoff

The repository is initialized on `main`; `origin` points to `https://github.com/sikunaniket1234/bharatvoice.git`, and the initial project commit has been pushed. The desktop can pull `origin/main`. Do not commit secrets or downloaded checkpoints.

## Laptop completion checklist

- [x] Verify Python venv creation and API tests.
- [x] Verify Node dependencies and NestJS tests/build.
- [x] Build/migrate the Angular PWA and test it in a browser.
- [x] Confirm the Angular → NestJS → FastAPI path and expected not-ready behavior.
- [x] Review `.gitignore`, environment files and staged changes.
- [x] Push the initial commit to origin.
- [x] Commit and push the Angular/Docker laptop milestone so the desktop can pull it.
