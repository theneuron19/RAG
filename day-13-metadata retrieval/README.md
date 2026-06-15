# Day 13 - Metadata-Aware Retrieval at Scale

**What this day teaches:** semantic similarity has no concept of *validity*. Ask "how many office days are required?" against an index holding three versions of the Remote Work Policy and all three retrieve - they're near-identical in embedding space. Which one is *current* is a structured-data question, not a semantic one. Day 13 answers it with a richer index schema and OData filters: vectors decide what's **relevant**, filters decide what's **eligible**.

## What's new

- A corpus built to expose the version trap, in `data-day13/`: 3 conflicting versions of the Remote Work Policy (1 -> 3 -> 2 office days), 2 versions of the Expense Policy ($50 -> $75 meal cap), plus a memo and an engineering spec for docType variety. Every PDF carries a **Document Control block** on page 1.
- **Metadata extraction at ingestion**: the control block is parsed into `docType`, `version`, `effectiveDate`, `author`, `department`, `status` - mined from the documents, not invented.
- A computed **`isLatest`** flag: group by title, sort by version, flag the highest. Superseded versions stay indexed (audit + "what changed?" queries) but are one filter away from exclusion.
- An **enriched index schema** where metadata fields are declared `filterable` / `facetable` / `sortable` - and a note on why this must be designed up front (Azure AI Search can't retrofit filterability without a rebuild).
- Query helpers combining `VectorizedQuery` with `filter=` (pre-filtering), four demos (version trap, by-author, department + date range, cross-version diff), and a **facets** cell that returns corpus value-counts like an e-commerce sidebar.

## How to run

1. `data-day13/` ships with all seven PDFs - no other data needed.
2. Provide Azure credentials via `config.json` or environment variables (same pattern as Days 1-12; inline fallbacks if `common/` is absent).
3. Open `day13_metadata_retrieval.ipynb`, pick your kernel, run top to bottom. It creates index `rag-corp-day13`.

## Done when

You can slice the corpus by structured attributes during retrieval - the unfiltered "office days" query returns conflicting versions, and `isLatest eq true` collapses it to the single correct answer (2 days, Policy v3.0).

## Why this matters in business

Enterprise corpora are version graveyards: policies, contracts, SOPs, specs - every one a family of revisions where only the newest is true. A RAG system that answers from a superseded policy isn't slightly wrong, it's confidently wrong, and in HR/finance/legal contexts that's a liability. Filters also pull double duty as the foundation for **security trimming** (filtering by user permissions) - the same mechanism, pointed at access control.

## Stacking with Day 12

Contextual retrieval (Day 12) puts document identity *inside* the vector; metadata (Day 13) puts it *beside* the vector where it can be filtered exactly. Production systems want both.
