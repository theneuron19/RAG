# Day 12 - Contextual Retrieval

**What this day teaches:** chunking is lossy. A chunk like "Revenue grew 3.4% over the previous quarter" is unambiguous inside its report and meaningless as a standalone index record - the company and quarter live in the document header, not the chunk. Contextual retrieval fixes this at **indexing time**: one LLM call per chunk writes a 1-2 sentence note situating the chunk in its document, and that note is prepended **before embedding**.

This is the indexing-time counterpart to Days 10-11, which expanded context at **query time**. The techniques stack.

## What's new

- A purpose-built ambiguous corpus in `data-day12/`: three fictional quarterly reports (NorthPeak Logistics Q1 + Q2, BlueHarbor Retail Q2) with near-identical section structure and phrasing - designed so raw chunks confuse companies and quarters.
- A `situate()` step: LLM sees the whole document + the chunk, returns a short context note (temperature 0).
- Two parallel indexes - `rag-finance-day12-raw` (baseline) and `rag-finance-day12-ctx` (contextualized) - and a `compare()` helper that runs the same query against both.
- A mini scorecard: 8 context-dependent questions scored on top-3 source accuracy (a preview of the Day 14 eval harness).

## How to run

1. `data-day12/` ships with the three PDFs - no other data needed.
2. Provide Azure credentials via `config.json` or environment variables (same pattern as Days 1-11; the notebook falls back to inline helpers if `common/` is absent).
3. Open `day12_contextual_retrieval.ipynb`, pick your kernel, run top to bottom. It creates both indexes.

## Done when

Contextualized chunks retrieve better on ambiguous queries - e.g., "How much did NorthPeak's revenue grow in Q2?" pulls the NorthPeak Q2 chunk, not BlueHarbor's identical-sounding one.

## Cost notes

- The situating calls are O(chunks) LLM calls, but **once per corpus at ingestion**, not per query.
- With prompt caching, the repeated full-document prefix is paid for roughly once per document, making this far cheaper than it looks.
- Query-time cost is unchanged - same number of calls, same context size as plain RAG.

## Why this matters in business

Real corpora are full of look-alike documents: monthly reports, contract versions, policies per region. When retrieval confuses them, the system answers confidently from the wrong document - the most dangerous failure mode there is. Contextual retrieval attacks that at the root, and the cost lands at ingestion (once) instead of at query time (forever).
