"""Embedding and vector retrieval helpers."""
from typing import Optional

from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


def embed_texts(client: AzureOpenAI, texts: list, deployment: str, batch_size: int = 16) -> list:
    out = []
    for i in range(0, len(texts), batch_size):
        resp = client.embeddings.create(model=deployment, input=texts[i:i + batch_size])
        out.extend(d.embedding for d in resp.data)
    return out


def embed(client: AzureOpenAI, text: str, deployment: str) -> list:
    return embed_texts(client, [text], deployment)[0]


def retrieve(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    query: str,
    embedding_deployment: str,
    k: int = 5,
    odata_filter: Optional[str] = None,
    select: Optional[list] = None,
    vector_field: str = "contentVector",
) -> list:
    """Vector retrieval with optional OData filter.

    Returns a list of dicts with the selected fields plus 'score'.
    """
    if select is None:
        select = ["content", "source"]

    vq = VectorizedQuery(
        vector=embed(openai_client, query, embedding_deployment),
        k_nearest_neighbors=k,
        fields=vector_field,
    )
    results = search_client.search(
        search_text=None,
        vector_queries=[vq],
        filter=odata_filter,
        select=select,
    )
    out = []
    for r in results:
        item = {f: r.get(f) for f in select}
        item["score"] = r["@search.score"]
        out.append(item)
    return out


def retrieve_keyword(
    search_client: SearchClient,
    query: str,
    k: int = 5,
    odata_filter: Optional[str] = None,
    select: Optional[list] = None,
) -> list:
    """Pure keyword (BM25) search — no embedding required.

    Use this when exact-term matching matters (codes, SKUs, IDs, version numbers).
    """
    if select is None:
        select = ["content", "source"]
    results = search_client.search(
        search_text=query,
        top=k,
        filter=odata_filter,
        select=select,
    )
    out = []
    for r in results:
        item = {f: r.get(f) for f in select}
        item["score"] = r["@search.score"]
        out.append(item)
    return out


def retrieve_hybrid(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    query: str,
    embedding_deployment: str,
    k: int = 5,
    odata_filter: Optional[str] = None,
    select: Optional[list] = None,
    vector_field: str = "contentVector",
) -> list:
    """Hybrid retrieval: keyword (BM25) + vector, fused with Reciprocal Rank Fusion.

    Azure AI Search applies RRF automatically when both search_text and
    vector_queries are provided. The returned score is the fused RRF score.
    """
    if select is None:
        select = ["content", "source"]

    vq = VectorizedQuery(
        vector=embed(openai_client, query, embedding_deployment),
        k_nearest_neighbors=k,
        fields=vector_field,
    )
    results = search_client.search(
        search_text=query,            # keyword side
        vector_queries=[vq],          # vector side
        top=k,                        # final k after fusion
        filter=odata_filter,
        select=select,
    )
    out = []
    for r in results:
        item = {f: r.get(f) for f in select}
        item["score"] = r["@search.score"]
        out.append(item)
    return out


def retrieve_with_rerank(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    query: str,
    embedding_deployment: str,
    semantic_config_name: str = "default-semantic",
    k: int = 5,
    odata_filter: Optional[str] = None,
    select: Optional[list] = None,
    vector_field: str = "contentVector",
) -> list:
    """Hybrid retrieval followed by semantic reranking (cross-encoder).

    Azure AI Search retrieves a wider candidate set internally and reorders
    it with a Microsoft-hosted cross-encoder. Returns the top-k after rerank.

    Each result carries TWO scores:
      - 'score' (the original BM25/vector/RRF score)
      - 'reranker_score' (the cross-encoder score, 0 to 4)

    Sort by reranker_score when judging quality post-rerank.
    """
    if select is None:
        select = ["content", "source"]

    vq = VectorizedQuery(
        vector=embed(openai_client, query, embedding_deployment),
        k_nearest_neighbors=50,            # wider net before reranking
        fields=vector_field,
    )
    results = search_client.search(
        search_text=query,
        vector_queries=[vq],
        top=k,                              # final top-k after rerank
        filter=odata_filter,
        select=select,
        query_type="semantic",
        semantic_configuration_name=semantic_config_name,
    )
    out = []
    for r in results:
        item = {f: r.get(f) for f in select}
        item["score"]          = r["@search.score"]
        item["reranker_score"] = r.get("@search.reranker_score", 0.0)
        out.append(item)
    return out


def retrieve_parent_documents(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    query: str,
    embedding_deployment: str,
    k_children: int = 10,
    n_parents: int = 3,
    odata_filter: Optional[str] = None,
    vector_field: str = "contentVector",
) -> list:
    """Small-to-big retrieval: match on small child chunks, return the parent passages.

    The index is expected to contain rows where each row has:
      - content        : the small CHILD chunk (embedded into contentVector)
      - parent_content : the larger PARENT passage the child belongs to
      - parent_id      : id of the parent (used for deduplication)

    We retrieve k_children child chunks, dedupe by parent_id (keeping the
    highest-scoring child per parent — children come back in score order),
    and return up to n_parents parent passages.

    Each returned dict has:
      - content        : the parent passage (sent to the LLM)
      - source, section: metadata
      - matched_child  : the small chunk that triggered the match (for debugging)
      - score          : retrieval score of the matching child
    """
    select = ["content", "parent_content", "parent_id", "source", "section"]
    vq = VectorizedQuery(
        vector=embed(openai_client, query, embedding_deployment),
        k_nearest_neighbors=k_children,
        fields=vector_field,
    )
    children = list(search_client.search(
        search_text=None,
        vector_queries=[vq],
        filter=odata_filter,
        select=select,
    ))

    parents = {}
    for c in children:
        pid = c.get("parent_id")
        if pid and pid not in parents:
            parents[pid] = {
                "content":       c["parent_content"],
                "source":        c.get("source"),
                "section":       c.get("section"),
                "parent_id":     pid,
                "matched_child": c["content"],
                "score":         c["@search.score"],
            }
        if len(parents) >= n_parents:
            break
    return list(parents.values())


def retrieve_parents(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    query: str,
    embedding_deployment: str,
    k_children: int = 15,
    k_parents: int = 5,
    odata_filter: Optional[str] = None,
    select: Optional[list] = None,
    vector_field: str = "contentVector",
) -> list:
    """Small-to-big retrieval. Matches on small child chunks, returns the larger
    parent sections those children belong to.

    Retrieves the top-k_children child chunks via vector search, dedupes by
    parent_id (so multiple matched children inside the same section produce
    only one parent), and returns up to k_parents unique parent sections.

    The returned dicts use `content` = the full parent text, so the result
    slots into existing answer()/format_context() helpers unchanged. The
    triggering child chunk is preserved as `matched_child` for transparency.

    Index requirements: each indexed document must carry `parent_id`
    and `parent_content` fields alongside the usual `content` and vector.
    """
    if select is None:
        select = ["content", "parent_content", "parent_id", "source", "section"]
    else:
        for f in ("parent_id", "parent_content"):
            if f not in select:
                select = list(select) + [f]

    vq = VectorizedQuery(
        vector=embed(openai_client, query, embedding_deployment),
        k_nearest_neighbors=k_children,
        fields=vector_field,
    )
    results = search_client.search(
        search_text=None,
        vector_queries=[vq],
        top=k_children,
        filter=odata_filter,
        select=select,
    )

    seen = {}
    for r in results:
        pid = r.get("parent_id")
        if not pid or pid in seen:
            continue
        seen[pid] = {
            "content":        r["parent_content"],   # the large parent text
            "matched_child":  r["content"],          # the small chunk that won
            "parent_id":      pid,
            "source":         r.get("source"),
            "section":        r.get("section"),
            "score":          r["@search.score"],
        }
        if len(seen) >= k_parents:
            break
    return list(seen.values())


def build_filter(
    category: Optional[str] = None,
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Optional[str]:
    """Build an OData filter string. since/until are ISO datetime strings (no quotes)."""
    clauses = []
    if category: clauses.append(f"category eq '{category}'")
    if author:   clauses.append(f"author eq '{author}'")
    if since:    clauses.append(f"date ge {since}")
    if until:    clauses.append(f"date lt {until}")
    return " and ".join(clauses) if clauses else None
