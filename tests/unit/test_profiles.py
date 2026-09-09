"""Unit tests for signing profile presets (T1)."""

from __future__ import annotations

import pytest

from golden_signing.signing.contracts import PusProfile, SignatureMode
from golden_signing.signing.profiles import (
    modern_pades_profile,
    profile_for_pus_kind,
    pus_safe_profile,
)

FP = "ab" * 32


def test_pus_safe_defaults() -> None:
    p = pus_safe_profile(certificate_fingerprint_sha256=FP)
    assert p.mode is SignatureMode.INVISIBLE
    assert p.pus_profile is PusProfile.PUS_SAFE
    assert p.verify_after_sign is True
    assert p.atomic_commit is True
    assert p.preserve_original is True
    assert p.filename_template == "{original_name}_signed.pdf"


def test_modern_pades_defaults() -> None:
    p = modern_pades_profile(certificate_fingerprint_sha256=FP)
    assert p.pus_profile is PusProfile.MODERN_PADES
    assert p.verify_after_sign is True


def test_profile_for_kind() -> None:
    assert profile_for_pus_kind(PusProfile.PUS_SAFE, certificate_fingerprint_sha256=FP).pus_profile is PusProfile.PUS_SAFE
    assert profile_for_pus_kind(PusProfile.MODERN_PADES, certificate_fingerprint_sha256=FP).pus_profile is PusProfile.MODERN_PADES
    with pytest.raises(ValueError):
        profile_for_pus_kind(PusProfile.CUSTOM, certificate_fingerprint_sha256=FP)


def test_preflight_result_extended_fields() -> None:
    from golden_signing.signing.contracts import PreflightLevel, PreflightResult

    r = PreflightResult(level=PreflightLevel.SAFE, page_count=4, encrypted=False)
    assert r.pdf_version is None
    assert r.file_size_bytes == 0
    assert r.writable is True
    assert r.has_acroform is False
    assert r.incremental_revisions == 0
