"""Document loading, chunking, and metadata parsing."""
import re
from pathlib import Path

from pypdf import PdfReader


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list:
    """Split text into overlapping chunks, preferring whitespace boundaries."""
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            window = text[start:end]
            brk = max(window.rfind("\n"), window.rfind(". "), window.rfind(" "))
            if brk > chunk_size * 0.5:
                end = start + brk + 1
        chunks.append(text[start:end].strip())
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def load_pdf_text(path: Path) -> str:
    """Extract all text from a single PDF."""
    reader = PdfReader(str(path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def load_pdfs(data_dir: Path) -> list:
    """Load every PDF from a directory. Returns list of {source, text}."""
    docs = []
    for path in sorted(Path(data_dir).glob("*.pdf")):
        docs.append({"source": path.name, "text": load_pdf_text(path)})
    return docs


def extract_sections(text: str, fallback: str = "Introduction") -> list:
    """Split text into (section_title, body) pairs by detecting '1. Title' patterns."""
    sections, current_title, current_body = [], fallback, []
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m and len(m.group(2)) < 80:
            if current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = m.group(2)
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_title, "\n".join(current_body).strip()))
    return [(t, b) for t, b in sections if b.strip()]


def parse_metadata_block(text: str, keys: tuple = ("category", "author", "date", "status", "project", "attendees")) -> dict:
    """Parse a 'Field: value' metadata block from the top of a document."""
    meta = {}
    for line in text.splitlines()[:25]:
        m = re.match(r"^([A-Za-z][A-Za-z ]*?)\s*:\s*(.+)$", line.strip())
        if m:
            key = m.group(1).strip().lower()
            if key in keys:
                meta[key] = m.group(2).strip()
    return meta
