"""ByteRange extract/validate and content-preservation hash helpers (spec §2.5, §11.3).

Phase 1 PDF Laboratory — structural baseline / integrity lane.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# /ByteRange [a b c d] — PDF 32000-1: four integers, offset/length pairs.
# Allow flexible whitespace (PDF name tokens are delimited by whitespace/delimiters).
_BR_RE = re.compile(
    rb"/ByteRange\s*\[\s*"
    rb"(\d+)\s+"
    rb"(\d+)\s+"
    rb"(\d+)\s+"
    rb"(\d+)\s*"
    rb"\]",
)


def extract_byte_range(pdf_bytes: bytes) -> list[int] | None:
    """Parse the first ``/ByteRange [a b c d]`` near a signature ``/Contents``.

    Returns the four integers as a list, or ``None`` if absent/malformed.
    """
    m = _BR_RE.search(pdf_bytes)
    if m is None:
        return None
    return [int(m.group(i)) for i in range(1, 5)]


def validate_byte_range(pdf_bytes: bytes, byte_range: list[int]) -> bool:
    """Validate a ByteRange against the file it is supposed to cover.

    Rules (spec §2.5 / §11.3):
    - exactly 4 non-negative integers;
    - first range starts at offset 0 (covers file head);
    - second range ends at EOF (covers file tail);
    - exactly one non-empty hole between them (the ``/Contents`` hex payload);
    - no overlap between the two ranges;
    - all range ends lie within the file size.
    """
    if not isinstance(byte_range, list) or len(byte_range) != 4:
        return False
    for v in byte_range:
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            return False

    a, b, c, d = byte_range
    size = len(pdf_bytes)

    # First range must start at 0 (otherwise there is an extra leading hole).
    if a != 0:
        return False

    # Ranges must lie within the file.
    if a + b > size or c + d > size or c > size:
        return False

    # Second range must end exactly at EOF (otherwise there is a trailing hole).
    if c + d != size:
        return False

    # Single non-empty hole: first range ends where second begins is forbidden
    # (zero-length hole) and overlap (a+b > c) is forbidden.
    return a + b < c


def sha256_bytes(data: bytes) -> str:
    """Return the hex digest of *data* (SHA-256)."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of the file at *path*.

    Raises ``OSError`` if the file cannot be read.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_range_hashes(pdf_bytes: bytes, byte_range: list[int]) -> tuple[bytes, bytes]:
    """Return SHA-256 digests of the two ByteRange-covered segments.

    Useful for content-preservation compare (spec §11.3): the same digests
    before and after an incremental signing update prove the covered bytes
    were not altered.
    """
    a, b, c, d = byte_range
    h1 = hashlib.sha256(pdf_bytes[a : a + b]).digest()
    h2 = hashlib.sha256(pdf_bytes[c : c + d]).digest()
    return (h1, h2)
