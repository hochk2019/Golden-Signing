"""Document type detection for queue intake (v1.1)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

__all__ = ["DocumentType", "detect_document_type", "is_office_ext"]

_PDF_MAGIC = b"%PDF-"
# ZIP container (docx/xlsx) and OLE compound (doc/xls)
_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class DocumentType(StrEnum):
    PDF = "PDF"
    WORD = "WORD"
    EXCEL = "EXCEL"
    UNKNOWN = "UNKNOWN"


_OFFICE_EXTS = {".doc", ".docx", ".xls", ".xlsx"}
_WORD_EXTS = {".doc", ".docx"}
_EXCEL_EXTS = {".xls", ".xlsx"}


def is_office_ext(path: Path) -> bool:
    return path.suffix.lower() in _OFFICE_EXTS


def detect_document_type(path: Path) -> DocumentType:
    """Prefer file magic; fall back to extension."""
    ext = path.suffix.lower()
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        head = b""
    if head.startswith(_PDF_MAGIC):
        return DocumentType.PDF
    if head.startswith(_ZIP_MAGIC) and ext in {".docx", ".xlsx"}:
        return (
            DocumentType.WORD
            if ext in _WORD_EXTS
            else DocumentType.EXCEL
        )
    if head.startswith(_OLE_MAGIC) and ext in {".doc", ".xls"}:
        return (
            DocumentType.WORD
            if ext in _WORD_EXTS
            else DocumentType.EXCEL
        )
    # Extension-only fallback (empty/unreadable header)
    if ext == ".pdf":
        return DocumentType.PDF
    if ext in _WORD_EXTS:
        return DocumentType.WORD
    if ext in _EXCEL_EXTS:
        return DocumentType.EXCEL
    return DocumentType.UNKNOWN
