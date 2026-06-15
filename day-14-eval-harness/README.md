# Day 14 - The RAG Evaluation Harness

**What this day teaches:** since Day 8 the project has shipped six retrieval upgrades, and the only evidence any of them helps has been "the demo looked better." Day 14 builds the yardstick: a reusable evaluation harness with a versioned eval set, deterministic retrieval metrics, LLM-judged generation metrics, a variant leaderboard, and timestamped regression files. Build it once, use it for every remaining day.

## What's in this folder

- `evalset_day14.json` - 20 questions over the **combined Day 12 + Day 13 corpora** (no new PDFs today; reusing the corpora is the point). Each item carries doc-level ground-truth sources, a reference answer, and a tag: `factual` or `history`.
- `day14_eval_harness.ipynb` - ingests both corpora into two indexes (raw and Day 12-contextualized), defines four pipeline variants, runs all 20 questions through each, scores, charts, and persists results.
- Outputs land in `results/`: `day14_leaderboard.png` and `day14_results_<timestamp>.json`.

## The four variants under test

| Variant | Index | Hybrid | Filter | Represents |
|---|---|---|---|---|
| `baseline` | raw chunks | no | none | Day 2 |
| `contextual` | situated chunks | no | none | Day 12 |
| `ctx+filter` | situated chunks | no | `isLatest eq true` | Day 13 |
| `hybrid+ctx+filter` | situated chunks | BM25+vector | `isLatest eq true` | Day 8 + 12 + 13 |

A variant is just `{index, hybrid, filter}` - the harness only needs `retrieve()` and `answer()`, which is what makes it reusable for Days 15-30.

## Metrics

- **Retrieval (deterministic, free):** hit@k, precision@k, MRR. Run on every change.
- **Generation (LLM-as-judge):** faithfulness (is the answer supported by the retrieved context?) and correctness (does it agree with the reference answer?). Run on candidate changes / nightly.

The pair matters because **faithful is not the same as correct**: an answer grounded perfectly in a superseded policy scores 1.0 on faithfulness and 0.0 on correctness. Measuring only faithfulness is how confident failures ship.

## How to run

1. Day 12 and Day 13 folders must sit alongside this one (the notebook reads `../day-12-contextual-retrieval/data-day12` and `../day-13-metadata-retrieval/data-day13`).
2. Azure credentials via `config.json` or environment variables, as in Days 1-13.
3. Run the notebook top to bottom. It creates indexes `rag-eval-day14-raw` and `rag-eval-day14-ctx`.

## Done when

Every Day 8-13 technique has a number next to it - including the per-tag split showing the `isLatest` filter lifting factual/current questions while breaking the history question (q20). That trade-off, invisible in demos and in aggregate scores, is the harness's reason to exist, and it points directly at query routing (choosing filters per query intent) later in the roadmap.

## Why this matters in business

An unevaluated RAG system can only be defended with anecdotes - and it regresses silently every time someone "improves" it. A harness turns pipeline changes into before/after diffs, makes quality a number stakeholders can track, and converts every production incident into a permanent test case. It is the difference between a demo and a system a company can depend on.
