"""PDF extraction and retrieval helpers for chat attachments."""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_MAX_CONTEXT_CHARS = 5000
DEFAULT_MAX_CONTEXT_CHUNKS = 5

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class ChunkScore:
    chunk: Dict[str, Any]
    score: float


def _tokenize(text: str) -> List[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text.lower())]
    return [t for t in tokens if t not in _STOPWORDS]


def _chunk_page_text(page_text: str, page_number: int) -> List[Dict[str, Any]]:
    text = " ".join(page_text.split())
    if not text:
        return []

    out: List[Dict[str, Any]] = []
    start = 0
    chunk_idx = 0
    step = max(1, DEFAULT_CHUNK_SIZE - DEFAULT_CHUNK_OVERLAP)

    while start < len(text):
        end = min(len(text), start + DEFAULT_CHUNK_SIZE)
        chunk_text = text[start:end].strip()
        if chunk_text:
            out.append(
                {
                    "chunk_id": f"p{page_number + 1}-c{chunk_idx + 1}",
                    "page_start": page_number + 1,
                    "page_end": page_number + 1,
                    "text": chunk_text,
                }
            )
            chunk_idx += 1
        if end >= len(text):
            break
        start += step
    return out


def _extract_with_pypdf(path: str) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    try:
        from pypdf import PdfReader
    except Exception as exc:  # noqa: BLE001
        return [], [f"pypdf_unavailable: {exc}"]

    try:
        reader = PdfReader(path)
    except Exception as exc:  # noqa: BLE001
        return [], [f"pypdf_read_failed: {exc}"]

    page_texts: List[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            page_texts.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"pypdf_page_extract_failed(page={idx + 1}): {exc}")
            page_texts.append("")
    return page_texts, warnings


def _is_ocr_enabled() -> bool:
    return os.getenv("GOBLIN_PDF_OCR_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _extract_with_ocr(path: str) -> Tuple[List[str], List[str]]:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except Exception as exc:  # noqa: BLE001
        return [], [f"ocr_deps_unavailable: {exc}"]

    try:
        images = convert_from_path(path)
    except Exception as exc:  # noqa: BLE001
        return [], [f"ocr_render_failed: {exc}"]

    page_texts: List[str] = []
    warnings: List[str] = []
    for idx, image in enumerate(images):
        try:
            page_texts.append(pytesseract.image_to_string(image) or "")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"ocr_page_extract_failed(page={idx + 1}): {exc}")
            page_texts.append("")
    return page_texts, warnings


def extract_pdf(path: str) -> Dict[str, Any]:
    """Extract PDF text/chunks and return structured metadata."""
    page_texts, warnings = _extract_with_pypdf(path)
    page_count = len(page_texts)
    text_char_count = sum(len(t.strip()) for t in page_texts if t)

    status = "success" if text_char_count > 0 else "no_text"
    ocr_attempted = False

    if text_char_count == 0 and _is_ocr_enabled():
        ocr_attempted = True
        ocr_page_texts, ocr_warnings = _extract_with_ocr(path)
        warnings.extend(ocr_warnings)
        ocr_char_count = sum(len(t.strip()) for t in ocr_page_texts if t)
        if ocr_char_count > 0:
            page_texts = ocr_page_texts
            page_count = len(page_texts)
            text_char_count = ocr_char_count
            status = "success"
        else:
            has_dep_warning = any("ocr_deps_unavailable" in w for w in ocr_warnings)
            status = "ocr_missing_deps" if has_dep_warning else "ocr_failed"

    chunks: List[Dict[str, Any]] = []
    for idx, page_text in enumerate(page_texts):
        chunks.extend(_chunk_page_text(page_text, idx))

    if text_char_count == 0 and not warnings:
        warnings.append("no_extractable_text")

    return {
        "pdf_extraction_status": status,
        "page_count": page_count,
        "char_count": text_char_count,
        "chunks": chunks,
        "warnings": warnings,
        "ocr_attempted": ocr_attempted,
    }


def select_relevant_chunks(
    *,
    query: str,
    chunks: List[Dict[str, Any]],
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> List[Dict[str, Any]]:
    """Pick top relevant chunks for a query using lexical overlap scoring."""
    query_tokens = _tokenize(query)
    if not query_tokens or not chunks:
        return []

    query_counts = Counter(query_tokens)
    query_set = set(query_counts.keys())
    scored: List[ChunkScore] = []

    for chunk in chunks:
        text = str(chunk.get("text", ""))
        chunk_tokens = _tokenize(text)
        if not chunk_tokens:
            continue
        chunk_counts = Counter(chunk_tokens)
        overlap = sum(min(chunk_counts[t], query_counts[t]) for t in query_set)
        if overlap <= 0:
            continue
        coverage = overlap / max(1, len(query_set))
        density = overlap / math.sqrt(max(1, len(chunk_tokens)))
        score = (2.0 * coverage) + density
        scored.append(ChunkScore(chunk=chunk, score=score))

    scored.sort(key=lambda item: item.score, reverse=True)

    selected: List[Dict[str, Any]] = []
    used_chars = 0
    for item in scored:
        if len(selected) >= max_chunks:
            break
        text = str(item.chunk.get("text", ""))
        if not text:
            continue
        if used_chars + len(text) > max_chars:
            remaining = max_chars - used_chars
            if remaining < 120:
                break
            truncated = dict(item.chunk)
            truncated["text"] = text[:remaining].rstrip() + "…"
            selected.append(truncated)
            break
        selected.append(item.chunk)
        used_chars += len(text)

    return selected


def build_attachment_context(
    *,
    query: str,
    attachments: List[Dict[str, Any]],
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """Build bounded context text from PDF attachment chunks."""
    sections: List[str] = []
    remaining_chars = max_chars
    remaining_chunks = max_chunks

    for attachment in attachments:
        if remaining_chunks <= 0 or remaining_chars <= 0:
            break
        if attachment.get("mime_type") != "application/pdf":
            continue

        chunks = attachment.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            continue

        selected = select_relevant_chunks(
            query=query,
            chunks=chunks,
            max_chunks=remaining_chunks,
            max_chars=remaining_chars,
        )
        if not selected:
            continue

        lines: List[str] = [f"Document: {attachment.get('filename', 'unknown.pdf')}"]
        for chunk in selected:
            page_start = chunk.get("page_start", "?")
            page_end = chunk.get("page_end", page_start)
            label = f"p.{page_start}" if page_start == page_end else f"p.{page_start}-{page_end}"
            lines.append(f"[{label}] {str(chunk.get('text', '')).strip()}")

        block = "\n".join(lines).strip()
        if not block:
            continue
        if len(block) > remaining_chars:
            block = block[:remaining_chars].rstrip()
        sections.append(block)
        remaining_chars -= len(block)
        remaining_chunks -= len(selected)

    if not sections:
        return ""

    return (
        "Attachment context extracted from user-provided PDFs. "
        "Use this only as supporting context for the current question.\n\n" + "\n\n".join(sections)
    )
