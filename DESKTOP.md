# Desktop AI development and handoff

## Intended role

The deployment plan identifies the developer desktop (Intel i5-11400, 16 GB RAM, NVIDIA GTX 1650 Super with 4 GB VRAM) as the primary AI development/inference machine. Keep PostgreSQL, Redis, NestJS and other non-AI services on CPU/RAM. Give GPU access only to the AI service when the host/container runtime is correctly configured.

Ubuntu Server 24.04 LTS is the preferred long-term deployment host; Windows can be used for development. This desktop is currently running Windows, so treat the measurements below as development-environment facts, not as a validated deployment-host configuration.

## Measured machine facts (recorded 2026-10-03)

Inspected directly on this desktop. These replace the previous "pending desktop inspection" status.

| Item | Measured value |
| --- | --- |
| OS | Windows 11 Pro, version `10.0.26200`, 64-bit |
| CPU | Intel Core i5-11400 @ 2.60 GHz, 6 cores / 12 logical processors |
| RAM | 15.87 GiB total; 5.63 GiB free at time of measurement |
| GPU | NVIDIA GeForce GTX 1650 SUPER, 4.00 GiB VRAM |
| VRAM in use at measurement | 1058 MiB resident (desktop/Chrome/WhatsApp/Edge), leaving roughly 3.0 GiB available to a model |
| NVIDIA driver | `591.86` (Windows driver version `32.0.15.9186`), driver date 2026-01-20 |
| CUDA version reported by `nvidia-smi` | `13.1` |
| GPU state | WDDM display mode, Compute mode `Default`, 46 °C, P8 idle at 9 W of a 100 W limit |
| Free disk | C: 268 GB, D: 447 GB, E: 1072 GB, F: 111 GB, G: 74 GB, J: 25 GB, K: 148 GB, L: 97 GB |
| Node.js / npm | Node `v24.18.0`, npm `11.16.0` |
| Python | `3.12.10` installed for this milestone; `3.14.7` and `3.10` also present |
| Docker | Docker Desktop on WSL2; CLI `29.7.2`, Compose `v5.4.0`, daemon verified reporting `linux` / `29.7.2` |
| Git | `2.55.0.windows.3`, branch `main`, remote `origin` |

The measured hardware matches the deployment plan's Profile B exactly. The one deviation is the host OS: it is Windows 11 Pro, not Ubuntu Server 24.04 LTS.
## Environment deviations that affect the AI milestone

1. **Windows, not Ubuntu — but GPU-in-Docker already works.** The deployment plan's step of installing the NVIDIA Container Toolkit is a Linux-host step and is **not required here**. Docker Desktop's WSL2 backend already passes the Windows driver through to Linux containers. Verified on this machine:

   ```powershell
   docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu22.04 nvidia-smi
   ```

   The container reported `NVIDIA GeForce GTX 1650 SUPER`, driver `591.86`, CUDA `13.1`, `4096 MiB` total VRAM with `916 MiB` already used by the desktop. No toolkit installation was performed.

   This means the `ai` service can be the only GPU consumer by adding a device reservation to its Compose service, and the gateway/web/PostgreSQL/Redis stay on CPU exactly as the plan requires.

2. **Inference must run in the Linux container, not the Windows virtualenv.** `IndicTransToolkit` supplies `IndicProcessor` only as a compiled Cython extension (`processor.pyx`, no pure-Python equivalent) and publishes **no `win_amd64` wheel for any Python version** — only `manylinux`, `musllinux` and `macosx_11_0_arm64`. A `cp312` `manylinux_x86_64` wheel does exist.

   Consequences:
   - `pip install -r requirements-ml.txt` fails on Windows with `Microsoft Visual C++ 14.0 or greater is required`.
   - Installing the Microsoft C++ Build Tools would make it compile, at the cost of a multi-gigabyte native toolchain on the host. **Not recommended.**
   - The supported path is the Docker `ai` service, which needs no compiler. This also matches the deployment plan, where the AI service is a container.

   Verified working in the built image: `torch 2.14.1+cu130`, `torch.cuda.is_available() == True`, device `NVIDIA GeForce GTX 1650 SUPER`, `transformers 4.57.6`, and `IndicTransToolkit.processor.IndicProcessor` importing cleanly.

   The Windows `.venv` is therefore kept contract-only. Do not try to add the ML extras to it.

3. **Readiness must verify weights, not just imports.** An early version reported `ready: true` because torch, transformers and IndicTransToolkit all imported, while every translation returned HTTP 502 because the gated checkpoints could not be downloaded. Readiness now probes the local cache and then makes a cheap Hugging Face metadata request, and reports `ready: false` with an actionable reason when a checkpoint is gated and no token has been supplied.

4. **`flash_attention_2` is unavailable on Windows.** The IndicTrans2 model cards recommend `attn_implementation="flash_attention_2"`, and explicitly say not to set it when flash-attn is absent. It is not set anywhere in this project.

5. **`transformers` is pinned below 5.0.0.** Both model cards warn that the `translation` pipeline was removed in transformers v5. These checkpoints are also `trust_remote_code` models, which are best matched to the 4.x line.

6. **PowerShell blocks `npm.ps1`.** The execution policy is `Restricted` on this host, so run `npm.cmd` (not `npm`) or the call fails before npm starts.

7. **npm requires install-script approval.** Five transitive dev packages (`@parcel/watcher`, `esbuild`, `lmdb`, `msgpackr-extract`, `unrs-resolver`) needed approval before the Angular build worked. The approved list is now recorded in `package.json`, so this only bites on an npm version that ignores it.

## Toolchain bug found and fixed on first pull

`apps/api-nestjs` had **no `types` restriction** in `tsconfig.json`, so TypeScript auto-included every hoisted `@types/*` package. The Angular workspace hoists `@types/jasmine` to the repository root, and its global `declare function expect<T>(actual: T): jasmine.Matchers<T>` shadowed Jest's `expect`, so `.rejects` did not exist and `npm run api:test` failed to compile:

```
TS2339: Property 'rejects' does not exist on type 'Matchers<Promise<TranslationResponseDto>>'.
```

Fixed by setting `"types": ["node", "jest"]` in `apps/api-nestjs/tsconfig.json`. This is a latent monorepo bug that would surface on any machine with the same hoisting layout, not a desktop-specific problem.

## First pull from laptop

1. Pull the latest laptop milestone from `origin/main`; the Angular PWA and Compose stack were pushed in commit `93e04ded58612dd880336780f35a0030c6b9b13f`.
2. Check out the recorded commit and read [README.md](README.md), [TASKS.md](TASKS.md), [LAPTOP.md](LAPTOP.md), this file and the three supplied source documents before changing architecture.
3. Install project dependencies using the repository lockfiles; do not install/download model weights into the repository.
4. Verify API tests and the CPU-only/not-ready path before configuring GPU inference.
5. Record the OS, NVIDIA driver, runtime/CUDA compatibility, free storage and GPU memory in this file once measured.

## Baseline verification completed on this desktop (2026-10-03)

Steps 1-5 above are done. The repository was cloned fresh at `bc82f1b`; Python 3.12.10 was installed to satisfy the documented `py -3.12` workflow; `npm approve-scripts` was granted for the five packages listed above.

| Check | Result |
| --- | --- |
| `npm ci` | Installed; five install scripts approved |
| `npm run api:build` | Pass |
| `npm run api:test` | 2/2 pass (after the `types` fix above) |
| `npm run web:test` | 3/3 pass, Chrome 154 headless |
| `pytest services/ai-fastapi` | 4/4 pass |
| `docker compose up --build -d` | All three services up; `ai` reports healthy |
| `GET http://127.0.0.1:4200` | HTTP 200 |
| `GET http://127.0.0.1:3000/api/v1/health` | HTTP 200 |
| `GET /health` inside the `ai` container | HTTP 200 `{"status":"ok","service":"ai-fastapi"}` |
| `GET /ready` inside the `ai` container | HTTP 503 `translation_provider_not_ready`, as designed |
| `POST /api/v1/translation` via the gateway | HTTP 503, as designed |

Confirmed: FastAPI is not published to a host port. It answers only from inside the Compose network, so `http://127.0.0.1:8000` on the host correctly refuses connections.

## Model milestone order

1. Start with IndicTrans2 distilled 200M, English → Odia; keep model ID/path configurable.
2. Measure cold start, warm latency, RAM/VRAM, and representative translation quality.
3. Add Odia → English and then English ↔ Hindi using the correct English→Indic and Indic→English checkpoints.
4. Store model name/version/license with results. Build a controlled bilingual evaluation set and human-review Odia quality.
5. Add Gemma only after this baseline and only for validated normalization/routing; never make it the authoritative translator.
6. Add ASR, TTS and transliteration incrementally. The 4 GB GPU is constrained: do not load all large models simultaneously; design model lifecycle/load-unload and queue behavior.

## Private pilot guardrails (later, not part of initial local work)

- Use Docker Compose for reproducible services after the AI baseline is understood.
- Keep PostgreSQL/Redis private; no inbound router port forwarding.
- If public access is later approved, use a limited outbound Cloudflare Tunnel and HTTPS, with authentication, rate limiting, backups, log rotation and monitoring.
- Define audio retention/cleanup and privacy rules before persisting recordings. Do not log raw audio or sensitive text unnecessarily.
- Treat a home desktop as a private pilot host, not highly available production infrastructure.

## Handoff record

- Git remote: `https://github.com/sikunaniket1234/bharatvoice.git` (`origin`).
- Branch: `main`; initial project commit: `9b3ee623eee7c9b850bd64aeed52ed38ef26cc5c`.
- Latest laptop frontend/Compose implementation commit: `93e04ded58612dd880336780f35a0030c6b9b13f` (`feat: add BharatVoice Angular PWA and Docker stack`).
- Desktop inspection commit: `bc82f1b` (`docs: update laptop completion and desktop handoff`) was the commit present at the first desktop pull.
- Desktop OS/driver/GPU measurements: recorded above on 2026-10-03 (Windows 11 Pro, driver 591.86, CUDA 13.1, 4.00 GiB VRAM, 15.87 GiB RAM).
- Model benchmark results: pending. Blocked on the gated Hugging Face checkpoints and on the unverified GPU-in-Docker path.
