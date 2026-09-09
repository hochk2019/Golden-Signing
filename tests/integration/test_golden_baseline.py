"""Integration: structural baseline on golden ECUS fixtures (T4)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.baseline import build_baseline, compare_baselines

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"
SIGNED_PDF = FIXTURES / "ecus_signed.pdf"

# From START_HERE.md — must remain stable
SOURCE_SHA256 = "76df3ed717a0077e4def2612005467ba8a21e095ffbe9dc076d14a150ec9b272"
SIGNED_SHA256 = "11921502135884cbdcd35f366dd2ccc7176c1d22843bd1efb4668f412cd8e475"


def test_source_baseline() -> None:
    b = build_baseline(SOURCE_PDF)
    assert b.page_count == 4
    assert b.encrypted is False
    assert b.has_acroform is False
    assert b.existing_signatures == []
    assert b.file_sha256 == SOURCE_SHA256


def test_signed_baseline_matches_ecus_structure() -> None:
    b = build_baseline(SIGNED_PDF)
    assert b.page_count == 4
    assert b.has_acroform is True
    assert len(b.existing_signatures) >= 1
    assert b.byte_range is not None
    assert b.byte_range_valid is True
    # Spec §2.2 sample used /Filter /Adobe.PPKMS and /SubFilter /adbe.pkcs7.sha1
    if b.sig_filter:
        assert "Adobe" in b.sig_filter or "PPKMS" in b.sig_filter or "adbe" in b.sig_filter.lower()
    if b.subfilter:
        assert "adbe.pkcs7" in b.subfilter or "ETSI" in b.subfilter or "CAdES" in b.subfilter
    assert b.file_sha256 == SIGNED_SHA256


def test_compare_source_vs_signed() -> None:
    src = build_baseline(SOURCE_PDF)
    signed = build_baseline(SIGNED_PDF)
    cmp = compare_baselines(src, signed)
    assert cmp["page_count_equal"] is True
    assert cmp["signed_has_acroform"] is True
    assert cmp["signed_byte_range_valid"] is True
    assert cmp["signed_existing_signatures"]
