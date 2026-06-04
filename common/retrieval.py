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
