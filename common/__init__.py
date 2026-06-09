"""rag-30-days — shared utilities for the RAG-on-Azure project.

Import the pieces you need:
    from common import load_config, get_openai_client, get_search_client
    from common import chunk_text, load_pdfs, extract_sections
    from common import embed, retrieve, build_filter
    from common import answer, answer_with_refusal, condense_query, verify_all
"""
from .config import load_config
from .clients import get_openai_client, get_search_client, get_search_index_client
from .ingestion import (
    chunk_text, load_pdfs, load_pdf_text,
    extract_sections, parse_metadata_block,
)
from .retrieval import embed, embed_texts, retrieve, retrieve_keyword, retrieve_hybrid, retrieve_with_rerank, retrieve_parents, build_filter
from .generation import (
    answer, answer_with_refusal, condense_query,
    parse_citations, verify_citation, verify_all, format_context,
    REFUSAL_SENTINEL,
)

__version__ = "0.1.0"
