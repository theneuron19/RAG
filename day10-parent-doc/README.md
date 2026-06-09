# Day 10 - Parent-Document Retrieval (Small-to-Big)

**What this day teaches:** retrieval needs small chunks for precision; generation needs full surrounding context for completeness. Small-to-big does both - match on children, generate from parents.

## What's new

- Two-level chunking: each document section is a *parent*; each parent is split into smaller *children*.
- Index schema adds `parent_id` and `parent_content` fields next to the usual content + vector.
- One new helper, `retrieve_parents()`, in `common/retrieval.py` - retrieves child hits, dedupes by parent_id, returns the parent sections in a shape that drops into the existing `answer()` function.

## How to run

1. Place the 3 enterprise policy PDFs in `../data-day10/` at the repo root.
2. Open `day10_parent_document_retrieval.ipynb`, pick your `.venv` kernel, run top to bottom.
3. The notebook creates index `rag-policies-day10`.

## Headline demo

Ask *"Can I return a custom-made item that arrived damaged?"*

- **Small-chunk RAG** matches the sentence *"custom-made items are generally not eligible for return"* and confidently answers "no, you can't."
- **Parent-doc RAG** matches the same sentence but sends the LLM the *full section*, which includes the next sentence: *"however, if a custom item arrives damaged, follow the defective items process."* The answer becomes the correct nuanced one.

That difference - between technically correct and practically correct - is what this technique delivers.

## Why this matters in business

Policy documents, contracts, legal text, and SOPs all share the same property: the exception is rarely in the same sentence as the rule. Any AI answering questions over this kind of content needs parent-style context, or it will give confidently wrong answers in exactly the cases that matter most.
