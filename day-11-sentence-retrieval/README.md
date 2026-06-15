# Day 11 - Sentence-Window Retrieval

**What this day teaches:** when the answer lives in just a few consecutive sentences, sending a full section to the LLM is wasteful. Sentence-window retrieves at sentence granularity and expands each hit to a small window of N neighbors.

## What's new

- Sentence-level indexing: each record is one sentence + a pre-computed `window` text containing the sentence plus its N neighbors.
- Retrieval uses `retrieve_windows()` from `common/retrieval.py` (already wired up); generation is unchanged.
- Comparison cells run against both the Day 10 parent-doc index and the new Day 11 sentence-window index so you can see the trade-off.

## How to run

1. Day 10's index (`rag-policies-day10`) must already exist.
2. PDFs already in `../data-day10/` from Day 10 - no new data.
3. Open `day11_sentence_window.ipynb`, pick your `.venv` kernel, run top to bottom.
4. The notebook creates the new index `rag-policies-day11`.

## When to use which

- **Focused factual question** ("when are credit card refunds posted?") -> sentence-window. Much less context, same correctness.
- **Nuanced policy question with exceptions across paragraphs** ("can I return a custom-made damaged item?") -> parent-doc. The exception is more likely to be in the section than in a small window.
- Production systems often run both and pick per question type.

## Why this matters in business

For high-volume customer support and chatbots, context-size reduction is a direct cost reduction. A much smaller context per query is a much cheaper generation call - which compounds quickly across millions of queries.
