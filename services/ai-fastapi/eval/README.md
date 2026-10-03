# Phase 1 translation evaluation set

## What this is

`phase1_smoke.jsonl` is a small, hand-authored **smoke set** covering the four
Phase 1 directions. It exists to prove the pipeline runs end to end, to catch
regressions, and to record latency/VRAM figures on this desktop. Each row has
one `id`, the `source_text`, a `reference_text`, and `tags`.

The tags deliberately cover the categories the technical documentation asks
for as regression cases:

| Tag | Why it is here |
| --- | --- |
| `greeting` | Very high frequency, short, and a common failure point for tokenizers |
| `daily` | Everyday sentence structure and verb agreement |
| `name` | Person names, which translation models often corrupt |
| `location` | Place names, including Odia-to-English rendering of Bhubaneswar |
| `date` | Numbers and dates, which reveal digit and calendar handling |
| `code-mixed-domain` | Latin technical terms that must survive into Indic script |
| `code-mixed` | Genuinely code-mixed Odia input, per the technical docs' regression requirement |

The `or_en_13` row is the PRD's own example, `ମୁଁ ଆଜି office ଯିବିନି।`, where
`office` is left in Latin script inside an Odia sentence.

## Important caveat about the scores

**Do not treat BLEU/chrF from this file as a translation-quality verdict.**

The references were written by hand for this project, not taken from an
independent corpus. That creates two problems:

1. They are only as good as one author's Odia and Hindi. The technical
   documentation explicitly requires human review of Odia quality, and that
   review has not happened yet.
2. Automatic metrics against self-authored references systematically flatter a
   model. A single valid reference per sentence hides every equally valid
   alternative, which is why BLEU looks punitive and chrF is usually preferred
   for Indic languages.

Treat the numbers as a **relative** signal for detecting regressions between
model or checkpoint versions, not as an absolute quality measure.

## What to use instead for real evaluation

The IndicTrans2 collection publishes standard benchmarks that this set should
eventually be replaced by or supplemented with:

- **FLORES-200** `devtest` — the standard multilingual evaluation set.
- **IN22-Gen** — generated sentences across the 22 scheduled Indic languages.
- **IN22-Conv** — conversational sentences, closest to the Phase 1
  conversation feature.

Whichever is used, record the dataset name, version and license alongside the
scores. Dataset licenses are tracked separately from model licenses.

## Running the benchmark

With the machine-learning extras installed:

```powershell
.\.venv\Scripts\python.exe services\ai-fastapi\scripts\benchmark_translation.py
```

Limit to specific directions with a repeatable flag:

```powershell
.\.venv\Scripts\python.exe services\ai-fastapi\scripts\benchmark_translation.py --direction en->or --direction or->en
```

Reports are written to `eval/reports/phase1_smoke_<timestamp>.json` and include
per-direction cold load time, warm latency mean/p50/p95/min/max, allocated and
reserved VRAM, process RAM, the checkpoint identifier, its license, the first
five sample outputs per direction, and any errors.

The script exits non-zero if any direction produced errors, so it can be used
as a gate. `eval/reports/` is generated output; add it to `.gitignore` unless a
report is deliberately being recorded as a milestone.