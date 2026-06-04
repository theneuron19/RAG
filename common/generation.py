"""Answer generation: basic, refusal-aware, conversational, and citation-verified."""
import re
from typing import Optional

from openai import AzureOpenAI


REFUSAL_SENTINEL = "INSUFFICIENT_INFORMATION"
CITE_RE = re.compile(r"\[(\d+)\]")


def format_context(hits: list, include_metadata: bool = True) -> str:
    """Format hits as numbered passages for prompt insertion."""
    parts = []
    for i, h in enumerate(hits, 1):
        if include_metadata:
            meta = []
            if h.get("source"):  meta.append(f"source: {h['source']}")
            if h.get("page"):    meta.append(f"page {h['page']}")
            if h.get("section"): meta.append(f"section: {h['section']}")
            tag = f" ({', '.join(meta)})" if meta else ""
            parts.append(f"[{i}]{tag}\n{h['content']}")
        else:
            parts.append(f"[{i}]\n{h['content']}")
    return "\n\n".join(parts)


def answer(
    client: AzureOpenAI,
    chat_deployment: str,
    question: str,
    hits: list,
    cite: bool = True,
) -> str:
    """Generate an answer strictly from retrieved chunks."""
    system = (
        "You answer questions strictly from the numbered context passages. "
        + ("Cite passage numbers like [1], [2] for every claim. " if cite else "")
        + "If the answer is not in the context, say you don't know based on the documents."
    )
    resp = client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Context:\n{format_context(hits)}\n\nQuestion: {question}"},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


# ---- Refusal (Day 3) ----

def answer_with_refusal(
    client: AzureOpenAI,
    chat_deployment: str,
    question: str,
    hits: list,
    score_threshold: float = 0.65,
) -> dict:
    """Two-layer refusal: score gate + sentinel-based model refusal."""
    top_score = hits[0]["score"] if hits else 0.0

    if not hits or top_score < score_threshold:
        return {"status": "refused-low-confidence",
                "answer": "I don't know based on the documents.",
                "top_score": top_score, "hits": hits}

    system = (
        "You answer questions from the numbered context passages. "
        f"If the answer is NOT in the passages, reply with exactly: {REFUSAL_SENTINEL}\n"
        "Otherwise, answer concisely and cite passage numbers like [1], [2]."
    )
    resp = client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Context:\n{format_context(hits)}\n\nQuestion: {question}"},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith(REFUSAL_SENTINEL):
        return {"status": "refused-by-model",
                "answer": "I don't know based on the documents.",
                "top_score": top_score, "hits": hits}
    return {"status": "answered", "answer": raw, "top_score": top_score, "hits": hits}


# ---- Conversational (Day 5) ----

CONDENSE_SYSTEM = (
    "You are a query rewriter for a question-answering system. "
    "Given chat history and a follow-up question, output a STANDALONE question. "
    "If already standalone, return unchanged. Resolve pronouns using history. "
    "On topic switches, do NOT inherit prior topic. Output ONLY the rewritten question."
)


def condense_query(client: AzureOpenAI, chat_deployment: str, history: list, question: str) -> str:
    """Rewrite a follow-up question as a standalone query using chat history."""
    if not history:
        return question
    history_text = "\n".join(f"User: {h['user']}\nAssistant: {h['assistant']}" for h in history)
    resp = client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": CONDENSE_SYSTEM},
            {"role": "user",   "content": f"History:\n{history_text}\n\nFollow-up: {question}\nStandalone:"},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


# ---- Citation verification (Day 6) ----

def parse_citations(answer_text: str, hits: list) -> list:
    """Return [{cite, sentence, passage}] for every [N] in the answer."""
    found = []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer_text.strip()) if s.strip()]
    for sent in sentences:
        for m in CITE_RE.finditer(sent):
            n = int(m.group(1))
            if 1 <= n <= len(hits):
                found.append({"cite": n, "sentence": sent, "passage": hits[n - 1]})
    return found


def verify_citation(client: AzureOpenAI, chat_deployment: str, claim: str, passage_text: str) -> str:
    """LLM-as-judge: returns SUPPORTED / PARTIAL / UNSUPPORTED."""
    system = (
        "You are a strict citation verifier. Decide whether the source passage "
        "SUPPORTS the claim sentence. Respond with exactly one word: "
        "SUPPORTED, PARTIAL, or UNSUPPORTED."
    )
    resp = client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Claim sentence: {claim}\n\nSource passage: {passage_text}\n\nVerdict:"},
        ],
        temperature=0,
        max_tokens=8,
    )
    verdict = resp.choices[0].message.content.strip().upper().split()[0]
    return verdict if verdict in ("SUPPORTED", "PARTIAL", "UNSUPPORTED") else "PARTIAL"


def verify_all(client: AzureOpenAI, chat_deployment: str, answer_text: str, hits: list) -> list:
    """Parse and verify all citations in an answer."""
    items = parse_citations(answer_text, hits)
    for it in items:
        it["verdict"] = verify_citation(client, chat_deployment, it["sentence"], it["passage"]["content"])
    return items
