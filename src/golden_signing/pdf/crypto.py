"""Open encrypted PDFs that use an empty user password (permission encryption)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["try_open_encrypted_with_empty_password"]


def _document_id1(reader: Any) -> bytes | None:
    try:
        idv = reader.trailer["/ID"]
        first = idv[0]
        if hasattr(first, "original_bytes"):
            return bytes(first.original_bytes)
        if isinstance(first, (bytes, bytearray)):
            return bytes(first)
        raw = str(first)
        # PDF hex string
        h = raw.strip("<>")
        if h and all(c in "0123456789abcdefABCDEF" for c in h) and len(h) % 2 == 0:
            return bytes.fromhex(h)
    except Exception:  # noqa: BLE001
        return None
    return None


def try_open_encrypted_with_empty_password(reader: Any) -> bool:
    """Attempt empty-user-password auth. True if readable without a real password."""
    if not getattr(reader, "encrypted", False):
        return True
    handler = getattr(reader, "security_handler", None)
    if handler is None:
        return False
    try:
        if callable(getattr(handler, "is_authenticated", None)) and handler.is_authenticated():
            return True
    except Exception:  # noqa: BLE001
        pass

    id1 = _document_id1(reader)
    try:
        result = handler.authenticate(b"", id1=id1)
    except Exception:  # noqa: BLE001
        # Some handlers ignore id1
        try:
            result = handler.authenticate(b"")
        except Exception:  # noqa: BLE001
            return False

    # AuthResult with USER/OWNER means empty password works
    status = getattr(result, "status", None)
    if status is None:
        try:
            return bool(handler.is_authenticated())
        except Exception:  # noqa: BLE001
            return False
    name = str(getattr(status, "name", status)).upper()
    return name in {"USER", "OWNER", "1", "2"} or int(status) >= 1  # type: ignore[arg-type]


def open_pdf_reader(path: Path, *, strict: bool = False) -> Any:
    """Open PdfFileReader; authenticate empty password when permission-encrypted.

    Raises if the file needs a real user password or is unreadable.
    """
    from pyhanko.pdf_utils.reader import PdfFileReader

    fh = open(path, "rb")  # noqa: SIM115 — caller owns lifetime via reader
    try:
        reader = PdfFileReader(fh, strict=strict)
        if reader.encrypted and not try_open_encrypted_with_empty_password(reader):
            fh.close()
            raise ValueError("PDF requires a password")
        # Keep file handle alive for reader
        reader._gs_fh = fh  # type: ignore[attr-defined]
        return reader
    except Exception:
        if not fh.closed:
            fh.close()
        raise
