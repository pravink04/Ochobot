"""Document loading, text extraction and chunking."""
import hashlib
import io
import re
from dataclasses import dataclass

from config import CHUNK_OVERLAP_WORDS, CHUNK_WORDS

SUPPORTED = {"pdf", "docx", "txt", "md", "xlsx"}


@dataclass
class Segment:
    text: str
    page: int      # 0 when the format has no pages
    section: str


def _guess_heading(text: str) -> str:
    first = text.strip().split("\n", 1)[0].strip()
    return first[:80] if 3 < len(first) <= 80 and not first.endswith(".") else ""


def load_pdf(data: bytes) -> list[Segment]:
    import pymupdf  # PyMuPDF
    segments = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for i, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if text:
                segments.append(Segment(text, i, _guess_heading(text)))
    return segments


def load_docx(data: bytes) -> list[Segment]:
    from docx import Document
    doc = Document(io.BytesIO(data))
    segments, heading, buf = [], "Introduction", []

    def flush():
        if buf:
            segments.append(Segment("\n".join(buf), 0, heading))
            buf.clear()

    for p in doc.paragraphs:
        if not p.text.strip():
            continue
        if p.style.name.lower().startswith("heading"):
            flush()
            heading = p.text.strip()[:80]
        else:
            buf.append(p.text.strip())
    flush()

    for t, table in enumerate(doc.tables, start=1):
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
        if rows:
            segments.append(Segment("\n".join(rows), 0, f"Table {t}"))
    return segments


def load_text(data: bytes) -> list[Segment]:
    text = data.decode("utf-8", errors="ignore").strip()
    if not text:
        return []
    # Split markdown/plain text on headings or blank-line-separated ALL-CAPS/numbered titles
    parts = re.split(r"\n(?=#{1,4} |\d+\.\s+[A-Z])", text)
    return [Segment(p.strip(), 0, _guess_heading(p.lstrip("# "))) for p in parts if p.strip()]


def load_xlsx(data: bytes) -> list[Segment]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    segments = []
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            segments.append(Segment("\n".join(rows), 0, f"Sheet: {ws.title}"))
    return segments


LOADERS = {"pdf": load_pdf, "docx": load_docx, "txt": load_text, "md": load_text, "xlsx": load_xlsx}


def chunk_segments(segments: list[Segment]) -> list[dict]:
    """Sliding-window word chunks that keep page/section metadata."""
    step = max(1, CHUNK_WORDS - CHUNK_OVERLAP_WORDS)
    chunks = []
    for seg in segments:
        words = seg.text.split()
        for start in range(0, len(words), step):
            window = words[start:start + CHUNK_WORDS]
            if len(window) < 15 and chunks and start > 0:
                break  # skip tiny trailing fragments
            chunks.append({
                "text": " ".join(window),
                "page": seg.page,
                "section": seg.section,
                "chunk_index": len(chunks),
            })
            if start + CHUNK_WORDS >= len(words):
                break
    return chunks


def ingest_file(store, filename: str, data: bytes) -> tuple[str, int, str]:
    """Returns (doc_id, n_chunks, status) where status is 'indexed' | 'duplicate' | 'empty'."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type: .{ext}")
    doc_id = hashlib.sha1(data).hexdigest()[:12]
    if store.has_document(doc_id):
        return doc_id, 0, "duplicate"
    chunks = chunk_segments(LOADERS[ext](data))
    if not chunks:
        return doc_id, 0, "empty"
    store.add_document(doc_id, filename, chunks)
    return doc_id, len(chunks), "indexed"