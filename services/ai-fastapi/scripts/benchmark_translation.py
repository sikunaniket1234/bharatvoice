"""Benchmark the IndicTrans2 provider over the controlled Phase 1 evaluation set.

Usage, from the repository root, with the machine-learning extras installed:

    .\\.venv\\Scripts\\python.exe services\\ai-fastapi\\scripts\\benchmark_translation.py

The script reports, per Phase 1 direction: cold model load time, warm latency
percentiles, allocated and reserved VRAM, peak host RAM, and BLEU/chrF against
the reference column. Results are written to
``services/ai-fastapi/eval/reports/<timestamp>.json``.

Read the caveat in ``eval/README.md`` before treating any score here as a
translation-quality verdict.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.config import MODEL_LICENSES, get_settings  # noqa: E402
from app.model_manager import get_manager  # noqa: E402
from app.providers.indictrans2 import IndicTrans2Provider  # noqa: E402
from app.schemas import TranslationRequest  # noqa: E402

DIRECTIONS = [("en", "or"), ("or", "en"), ("en", "hi"), ("hi", "en")]


def load_dataset(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise SystemExit(f"{path}:{line_number} is not valid JSON: {error}") from error
    if not rows:
        raise SystemExit(f"{path} contains no evaluation rows.")
    return rows


def host_ram_snapshot_mb() -> float:
    try:
        import psutil
    except ImportError:
        return 0.0
    return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return round(ordered[index], 3)


def score(hypotheses: list[str], references: list[str]) -> dict[str, float]:
    try:
        import sacrebleu
    except ImportError:
        return {}
    bleu = sacrebleu.corpus_bleu(hypotheses, [references])
    chrf = sacrebleu.corpus_chrf(hypotheses, [references])
    return {
        "bleu": round(bleu.score, 2),
        "chrf": round(chrf.score, 2),
        "bleu_signature": str(bleu.get_signature()),
    }


async def run_direction(
    provider: IndicTrans2Provider,
    manager,
    rows: list[dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    await manager.acquire(provider.settings.model_for(rows[0]["source_language"]))
    cold_load = manager.stats.load_seconds

    hypotheses: list[str] = []
    references: list[str] = []
    latencies: list[float] = []
    errors: list[dict[str, str]] = []
    samples: list[dict[str, str]] = []

    for row in rows:
        request = TranslationRequest(
            text=row["source_text"],
            source_language=row["source_language"],
            target_language=row["target_language"],
        )
        started = time.perf_counter()
        try:
            response = await provider.translate(request)
        except Exception as error:
            errors.append({"id": row["id"], "error": f"{type(error).__name__}: {error}"})
            continue
        latencies.append(time.perf_counter() - started)
        hypotheses.append(response.translated_text)
        references.append(row["reference_text"])
        if len(samples) < 5:
            samples.append(
                {
                    "id": row["id"],
                    "source": row["source_text"],
                    "hypothesis": response.translated_text,
                    "reference": row["reference_text"],
                }
            )

    allocated, reserved = manager.vram_snapshot()

    return {
        "direction": label,
        "checkpoint": manager.stats.model_id,
        "license": MODEL_LICENSES.get(manager.stats.model_id or "", "unknown"),
        "samples": len(rows),
        "translated": len(hypotheses),
        "errors": errors,
        "cold_load_seconds": round(cold_load, 3) if cold_load else None,
        "warm_latency_seconds": {
            "mean": round(statistics.fmean(latencies), 3) if latencies else None,
            "p50": percentile(latencies, 0.5),
            "p95": percentile(latencies, 0.95),
            "min": percentile(latencies, 0.0),
            "max": percentile(latencies, 1.0),
        },
        "allocated_vram_mb": round(allocated / (1024 * 1024), 1) if allocated else None,
        "reserved_vram_mb": round(reserved / (1024 * 1024), 1) if reserved else None,
        "process_ram_mb": host_ram_snapshot_mb(),
        "metrics": score(hypotheses, references) if hypotheses else {},
        "sample_outputs": samples,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=SERVICE_ROOT / "eval" / "phase1_smoke.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=SERVICE_ROOT / "eval" / "reports")
    parser.add_argument(
        "--direction",
        action="append",
        choices=[f"{a}->{b}" for a, b in DIRECTIONS],
        help="Limit to specific directions; repeatable. Defaults to all four.",
    )
    args = parser.parse_args()

    settings = get_settings()
    manager = get_manager()
    provider = IndicTrans2Provider(settings=settings, manager=manager)

    if not provider.is_ready:
        print("Provider is not ready. Install the machine-learning extras first:\n")
        print("  pip install --extra-index-url https://download.pytorch.org/whl/cu128 \\")
        print("      -r services/ai-fastapi/requirements-ml.txt\n")
        print(f"Readiness detail: {json.dumps(provider.status, indent=2, ensure_ascii=False)}")
        return 1

    rows = load_dataset(args.dataset)
    selected = set(args.direction or [f"{a}->{b}" for a, b in DIRECTIONS])

    torch_version = ""
    try:
        import torch

        torch_version = torch.__version__
    except ImportError:
        pass

    print(f"device={settings.device} dtype={settings.dtype} torch={torch_version}")
    print(f"checkpoints: {settings.en_indic_model} | {settings.indic_en_model}")
    print(f"token present: {bool(settings.hf_token)}")
    print()

    results = []
    for source, target in DIRECTIONS:
        label = f"{source}->{target}"
        if label not in selected:
            continue
        direction_rows = [
            row
            for row in rows
            if row["source_language"] == source and row["target_language"] == target
        ]
        if not direction_rows:
            continue
        print(f"running {label} ({len(direction_rows)} rows) ...", flush=True)
        result = await run_direction(provider, manager, direction_rows, label)
        results.append(result)
        latency = result["warm_latency_seconds"]
        metrics = result["metrics"]
        print(
            f"  {result['translated']}/{result['samples']} translated | "
            f"cold {result['cold_load_seconds']}s | "
            f"warm p50 {latency['p50']}s p95 {latency['p95']}s | "
            f"VRAM {result['allocated_vram_mb']}MB | "
            f"BLEU {metrics.get('bleu')} chrF {metrics.get('chrf')}"
        )
        if result["errors"]:
            print(f"  ERRORS: {result['errors'][:3]}", flush=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch_version,
            "device": settings.device,
            "dtype": settings.dtype,
            "num_beams": settings.num_beams,
            "batch_size": settings.batch_size,
            "hf_token_supplied": bool(settings.hf_token),
        },
        "dataset": str(args.dataset),
        "results": results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = args.output_dir / f"phase1_smoke_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"report written to {report_path}")
    return 0 if all(not r["errors"] for r in results) else 2


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    raise SystemExit(asyncio.run(main()))