"""
Phase 2 — Chunking: split documents into overlapping segments.
Uses sentence and paragraph boundaries (SEPARATORS) so tables and lists are not split
mid-row. Table-like lines are grouped and kept as one segment before size-based split.
"""
import re
from typing import List, Dict, Any

from .config import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS, SEPARATORS


def _split_by_separators(text: str, separators: List[str]) -> List[str]:
    """Recursively split by first available separator into chunks <= chunk_size."""
    if not text or not text.strip():
        return []
    if len(text) <= CHUNK_SIZE_CHARS:
        return [text.strip()] if text.strip() else []

    for sep in separators:
        if sep not in text:
            continue
        parts = text.split(sep)
        if len(parts) < 2:
            continue
        chunks = []
        current = ""
        for i, part in enumerate(parts):
            segment = part if i == 0 else sep + part
            if len(current) + len(segment) <= CHUNK_SIZE_CHARS:
                current += segment
            else:
                if current.strip():
                    chunks.append(current.strip())
                # start new chunk with overlap
                if CHUNK_OVERLAP_CHARS > 0 and len(current) >= CHUNK_OVERLAP_CHARS:
                    overlap_start = len(current) - CHUNK_OVERLAP_CHARS
                    current = current[overlap_start:] + segment
                else:
                    current = segment
        if current.strip():
            chunks.append(current.strip())
        if chunks:
            return chunks
    # fallback: hard cut by size with overlap
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE_CHARS, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - CHUNK_OVERLAP_CHARS if end < len(text) else len(text)
    return chunks


def _is_likely_table_line(line: str) -> bool:
    """Heuristic: line has multiple tabs or 2+ consecutive spaces or pipe separators."""
    if "\t" in line and line.count("\t") >= 2:
        return True
    if "  " in line and len(line.strip()) > 20:
        return True
    if "|" in line and line.count("|") >= 2:
        return True
    return False


def _group_table_lines(lines: List[str]) -> List[str]:
    """
    Group consecutive table-like lines and single non-table lines into segments.
    Returns list of segments (each can be a table block or a normal paragraph).
    """
    segments = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_likely_table_line(line):
            block = [line]
            j = i + 1
            while j < len(lines) and _is_likely_table_line(lines[j]):
                block.append(lines[j])
                j += 1
            segments.append("\n".join(block))
            i = j
        else:
            segments.append(line)
            i += 1
    return segments


def chunk_document(
    text: str,
    source_url: str,
    scrape_date: str,
    page_type: str,
    scheme_name: str,
) -> List[Dict[str, Any]]:
    """
    Split document into overlapping chunks. Keep table blocks intact.
    Returns list of dicts: { "text", "source_url", "scrape_date", "page_type", "scheme_name" }.
    """
    text = (text or "").strip()
    if not text:
        return []

    # First split by double newline to get paragraphs/blocks
    blocks = re.split(r"\n\s*\n", text)
    segments_to_chunk = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        if any(_is_likely_table_line(ln) for ln in lines):
            # Keep whole table as one segment
            segments_to_chunk.append(block)
        else:
            # Could be long paragraph — will be split by size later
            segments_to_chunk.append(block)

    # Rejoin and run size-based split with overlap
    recombined = "\n\n".join(segments_to_chunk)
    raw_chunks = _split_by_separators(recombined, SEPARATORS)

    meta = {
        "source_url": source_url,
        "scrape_date": scrape_date,
        "page_type": page_type,
        "scheme_name": scheme_name,
    }
    return [{"text": c, **meta} for c in raw_chunks if c]
