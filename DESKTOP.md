# Desktop AI development and handoff

## Intended role

The deployment plan identifies the developer desktop (Intel i5-11400, 16 GB RAM, NVIDIA GTX 1650 Super with 4 GB VRAM) as the primary AI development/inference machine. Keep PostgreSQL, Redis, NestJS and other non-AI services on CPU/RAM. Give GPU access only to the AI service when the host/container runtime is correctly configured.

Ubuntu Server 24.04 LTS is the preferred long-term deployment host; Windows can be used for development. The desktop OS, driver, CUDA/container runtime, free disk space and actual GPU availability have not been inspected from this laptop session. Confirm those facts before running OS-specific install commands.

## First pull from laptop

1. After the laptop milestone is committed and pushed, use the agreed repository URL and branch to clone/pull this project on the desktop.
2. Check out the recorded commit and read [README.md](README.md), [TASKS.md](TASKS.md), [LAPTOP.md](LAPTOP.md), this file and the three supplied source documents before changing architecture.
3. Install project dependencies using the repository lockfiles; do not install/download model weights into the repository.
4. Verify API tests and the CPU-only/not-ready path before configuring GPU inference.
5. Record the OS, NVIDIA driver, runtime/CUDA compatibility, free storage and GPU memory in this file once measured.

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

- Git remote: `https://github.com/sikunaniket1234/bharatvoice.git` (`origin`). Record the pushed commit hash after the laptop initial commit is pushed.
- Branch: `main`.
- Desktop OS/driver/GPU runtime measurements: pending desktop inspection.
- Model benchmark results: pending.
