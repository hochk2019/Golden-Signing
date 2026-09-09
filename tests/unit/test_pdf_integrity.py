"""Unit tests for PDF ByteRange integrity helpers (T3)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from golden_signing.pdf.integrity import (
    content_range_hashes,
    extract_byte_range,
    sha256_bytes,
    sha256_file,
    validate_byte_range,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "private" / "ecus_signed.pdf"

# Spec §2.5 sample shape (Golden Signing v1.2.0.md)
EXPECTED_BR = [0, 313171, 321173, 33265]


def _load_fixture() -> bytes:
    if not FIXTURE.exists():
        pytest.skip(f"private fixture missing: {FIXTURE}")
    return FIXTURE.read_bytes()


def _make_synthetic_pdf() -> bytes:
    """Minimal PDF-like bytes with a fixed-width /ByteRange and /Contents placeholder.

    The ByteRange hole covers the full ``/Contents <hex>`` value including the
    angle-bracket delimiters, matching real PDF signing convention.
    """
    hex_data = b"AB" * 50  # 100 hex chars (50 raw bytes of fake CMS)
    head = b"%PDF-1.4\n1 0 obj\n<< /Type /Sig "
    mid = b" /Contents "  # ends just before the opening '<'
    hole = b"<" + hex_data + b">"
    tail = b" >>\nendobj\n%%EOF\n"
    # Fixed-width integers so the /ByteRange token length is constant.
    br_template = b"/ByteRange [0 %08d %08d %08d ]"
    br_len = len(br_template % (0, 0, 0))
    a = len(head) + br_len + len(mid)
    c = a + len(hole)
    d = len(tail)
    br = br_template % (a, c, d)
    assert len(br) == br_len
    return head + br + mid + hole + tail


# ---------------------------------------------------------------------------
# extract_byte_range
# ---------------------------------------------------------------------------


def test_extract_real_fixture_returns_four_ints() -> None:
    data = _load_fixture()
    br = extract_byte_range(data)
    assert br is not None
    assert len(br) == 4
    assert all(isinstance(v, int) for v in br)
    assert br == EXPECTED_BR


def test_extract_synthetic() -> None:
    data = _make_synthetic_pdf()
    br = extract_byte_range(data)
    assert br is not None
    assert len(br) == 4
    assert br[0] == 0


def test_extract_missing_returns_none() -> None:
    assert extract_byte_range(b"%PDF-1.4\nno signature here\n%%EOF\n") is None


def test_extract_malformed_returns_none() -> None:
    assert extract_byte_range(b"/ByteRange [0 10 not-an-int 20 ]") is None
    assert extract_byte_range(b"/ByteRange [0 10 20 ]") is None  # only 3 ints


# ---------------------------------------------------------------------------
# validate_byte_range
# ---------------------------------------------------------------------------


def test_validate_real_fixture_true() -> None:
    data = _load_fixture()
    br = extract_byte_range(data)
    assert br is not None
    assert validate_byte_range(data, br) is True


def test_validate_real_fixture_hole_covers_contents() -> None:
    data = _load_fixture()
    br = extract_byte_range(data)
    assert br is not None
    a, b, c, d = br
    hole = data[a + b : c]
    # The hole is the /Contents hex string including angle-bracket delimiters
    # (standard PDF ByteRange: the whole /Contents value is excluded).
    assert hole.startswith(b"<")
    assert hole.endswith(b">")
    # Interior is hex digits only (CMS DER payload).
    inner = hole[1:-1]
    assert inner[:1] == b"3"  # DER CMS starts with 0x30 → hex '3'
    assert all(chr(x) in "0123456789abcdefABCDEF" for x in inner)
    # Second range ends at EOF.
    assert c + d == len(data)


def test_validate_synthetic_true() -> None:
    data = _make_synthetic_pdf()
    br = extract_byte_range(data)
    assert br is not None
    assert validate_byte_range(data, br) is True


def test_validate_truncated_file_false() -> None:
    data = _load_fixture()
    br = extract_byte_range(data)
    assert br is not None
    truncated = data[:-100]
    assert validate_byte_range(truncated, br) is False


def test_validate_range_exceeds_size_false() -> None:
    data = _load_fixture()
    bad = [0, 313171, 321173, 999999]  # second length overruns EOF
    assert validate_byte_range(data, bad) is False


def test_validate_wrong_length_false() -> None:
    data = _make_synthetic_pdf()
    assert validate_byte_range(data, [0, 10, 20]) is False
    assert validate_byte_range(data, [0, 10, 20, 30, 40]) is False


def test_validate_negative_false() -> None:
    data = _make_synthetic_pdf()
    assert validate_byte_range(data, [0, -1, 20, 30]) is False
    assert validate_byte_range(data, [-1, 10, 20, 30]) is False


def test_validate_overlap_false() -> None:
    data = _make_synthetic_pdf()
    size = len(data)
    # Ranges overlap: first ends after second starts.
    bad = [0, size - 10, size - 20, 20]
    assert validate_byte_range(data, bad) is False


def test_validate_gap_before_first_range_false() -> None:
    data = _make_synthetic_pdf()
    size = len(data)
    # First range does not start at 0 → extra hole before it.
    bad = [5, size - 30, size - 10, 10]
    assert validate_byte_range(data, bad) is False


def test_validate_second_range_not_to_eof_false() -> None:
    data = _make_synthetic_pdf()
    size = len(data)
    # Second range ends before EOF → trailing hole.
    bad = [0, 10, 20, size - 40]
    assert validate_byte_range(data, bad) is False


def test_validate_empty_hole_false() -> None:
    data = _make_synthetic_pdf()
    size = len(data)
    # a+b == c → zero-length hole (no /Contents gap).
    bad = [0, 50, 50, size - 50]
    assert validate_byte_range(data, bad) is False


def test_validate_non_int_false() -> None:
    data = _make_synthetic_pdf()
    assert validate_byte_range(data, [0, 1.5, 20, 30]) is False  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# sha256 helpers
# ---------------------------------------------------------------------------


def test_sha256_bytes() -> None:
    assert sha256_bytes(b"hello") == hashlib.sha256(b"hello").hexdigest()
    assert len(sha256_bytes(b"")) == 64


def test_sha256_file(tmp_path: Path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"golden")
    assert sha256_file(p) == hashlib.sha256(b"golden").hexdigest()


def test_sha256_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        sha256_file(tmp_path / "nope.bin")


# ---------------------------------------------------------------------------
# content_range_hashes
# ---------------------------------------------------------------------------


def test_content_range_hashes_real_fixture() -> None:
    data = _load_fixture()
    br = extract_byte_range(data)
    assert br is not None
    a, b, c, d = br
    h1, h2 = content_range_hashes(data, br)
    assert h1 == hashlib.sha256(data[a : a + b]).digest()
    assert h2 == hashlib.sha256(data[c : c + d]).digest()
    assert len(h1) == 32
    assert len(h2) == 32
    assert h1 != h2


def test_content_range_hashes_synthetic() -> None:
    data = _make_synthetic_pdf()
    br = extract_byte_range(data)
    assert br is not None
    a, b, c, d = br
    h1, h2 = content_range_hashes(data, br)
    assert h1 == hashlib.sha256(data[a : a + b]).digest()
    assert h2 == hashlib.sha256(data[c : c + d]).digest()


def test_content_range_hashes_detects_tamper_outside_hole() -> None:
    """Changing a byte in a covered range changes that range's digest."""
    data = bytearray(_make_synthetic_pdf())
    br = extract_byte_range(bytes(data))
    assert br is not None
    a, b, c, d = br
    orig = content_range_hashes(bytes(data), br)
    # Flip a byte inside the first covered range (after header, before hole).
    data[a + 5] ^= 0xFF
    tampered = content_range_hashes(bytes(data), br)
    assert tampered[0] != orig[0]
    assert tampered[1] == orig[1]
