"""Rule-based requirement extraction (SRS .docx -> requirement list)."""

from app.agents.project_planning.extraction.extractor import (
    extract_from_bytes,
    extract_from_path,
)

__all__ = ["extract_from_bytes", "extract_from_path"]
