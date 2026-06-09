# Day 9 — Semantic Reranking

**What this day teaches:** Day 8 retrieves plenty of relevant candidates; Day 9 makes sure the *most* relevant one ranks first. A cross-encoder model reads the original question alongside each candidate chunk and reorders by true relevance.

## What's new

- Index now carries a `SemanticConfiguration` (Azure AI Search semantic ranker).
- One new helper in `common/retrieval.py`: `retrieve_with_rerank()` returns both the original retrieval score and the cross-encoder `reranker_score` (0–4 range).
- Demos contrast hybrid-only vs hybrid+rerank ordering on paraphrased / cross-document / vague questions — the reranker's strengths.

## How to run

1. PDFs already in `../data-day8/` from Day 8 — no new data.
2. Open `day09_reranking.ipynb`, pick your `.venv` kernel, run top to bottom.
3. The notebook creates `rag-techdocs-day9` index (separate from Day 8's index).

## Prerequisites

- **Azure AI Search tier must support semantic ranker** — Free tier does NOT. Basic or Standard works.
- Semantic ranker has its own transaction quota (1000/month free on most regions).

## Why this matters in business

For high-stakes Q&A — legal research, medical reference, financial analysis — the difference between "the AI found something" and "the AI found the *right* thing" is reranking. It's the highest-precision boost available without changing models, infrastructure, or data.
