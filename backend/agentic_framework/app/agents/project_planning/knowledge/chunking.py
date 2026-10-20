"""Lightweight text chunker for expanding the knowledge corpus.

The current seed data consists of short, self-contained rows (9–11 records per
collection) that do not need chunking.  This module exists to support **future
corpus expansion** with longer documents (`.md`, `.txt`, `.docx` extracts):

* ``chunk_by_heading`` — splits on Markdown headings, keeping hierarchy metadata.
* ``chunk_by_tokens`` — fixed-size token window with configurable overlap.

Both return ``Chunk`` objects ready to be added to a ChromaDB collection.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single text chunk ready for embedding and insertion."""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Heading-based chunker (for Markdown / structured text)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def chunk_by_heading(
    text: str,
    *,
    source_id: str = "",
    min_chunk_tokens: int = 30,
) -> list[Chunk]:
    """Split *text* on Markdown headings, preserving section path metadata.

    Sections shorter than *min_chunk_tokens* (whitespace-split) are merged
    with the next section to avoid tiny fragments.
    """
    if not text.strip():
        return []

    parts: list[tuple[str, str, int]] = []  # (heading, body, level)
    last_end = 0
    for m in _HEADING_RE.finditer(text):
        if last_end < m.start():
            body = text[last_end : m.start()].strip()
            if body:
                heading = parts[-1][0] if parts else ""
                level = parts[-1][2] if parts else 0
                parts.append((heading, body, level))
        heading_text = m.group(2).strip()
        level = len(m.group(1))
        last_end = m.end()
        parts.append((heading_text, "", level))

    # Trailing text after the last heading
    trailing = text[last_end:].strip()
    if trailing:
        if parts:
            heading, body, level = parts[-1]
            parts[-1] = (heading, (body + "\n\n" + trailing).strip(), level)
        else:
            parts.append(("", trailing, 0))

    # Merge heading entries with their body
    merged: list[tuple[str, str, int]] = []
    for heading, body, level in parts:
        if not body and merged:
            # Empty body — this is a heading-only line, attach to next
            continue
        merged.append((heading, body, level))

    # Build section path and chunks
    path_stack: list[str] = []
    chunks: list[Chunk] = []
    for heading, body, level in merged:
        if not body:
            continue
        # Maintain heading hierarchy
        path_stack = path_stack[: max(level - 1, 0)]
        if heading:
            path_stack.append(heading)
        section_path = " > ".join(path_stack) if path_stack else ""

        # Skip tiny fragments
        if len(body.split()) < min_chunk_tokens and chunks:
            # Append to previous chunk
            prev = chunks[-1]
            prev.text += "\n\n" + body
            continue

        chunks.append(Chunk(
            id=f"{source_id}_{uuid.uuid4().hex[:8]}" if source_id else uuid.uuid4().hex[:12],
            text=body,
            metadata={"source": source_id, "section": section_path},
        ))

    return chunks


# ---------------------------------------------------------------------------
# Token-window chunker (for flat text)
# ---------------------------------------------------------------------------


def chunk_by_tokens(
    text: str,
    *,
    source_id: str = "",
    max_tokens: int = 450,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    """Split *text* into approximately *max_tokens*-sized chunks with overlap.

    Token counting is whitespace-split (a rough proxy — accurate enough for
    retrieval chunking without pulling in a tokenizer dependency).
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= max_tokens:
        return [Chunk(
            id=f"{source_id}_{uuid.uuid4().hex[:8]}" if source_id else uuid.uuid4().hex[:12],
            text=text,
            metadata={"source": source_id, "chunk_index": 0},
        )]

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(Chunk(
            id=f"{source_id}_{uuid.uuid4().hex[:8]}" if source_id else uuid.uuid4().hex[:12],
            text=chunk_text,
            metadata={"source": source_id, "chunk_index": idx},
        ))
        if end >= len(words):
            break
        start = end - overlap_tokens
        idx += 1

    return chunks
