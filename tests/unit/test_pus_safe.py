"""Unit tests for PUS Safe settings resolution (T1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from golden_signing.signing.contracts import PusProfile, SignatureMode
from golden_signing.signing.profiles import modern_pades_profile, pus_safe_profile
from golden_signing.signing.pus_safe import (
    ProfileInvariantError,
    assert_pus_safe_invariants,
    resolve_signing_settings,
)

FP = "ab" * 32


def test_pus_safe_resolves_forced_verify() -> None:
    p = pus_safe_profile(certificate_fingerprint_sha256=FP)
    # even if someone tampers verify flag off
    p.verify_after_sign = False
    s = resolve_signing_settings(p)
    assert s.verify_after_sign is True
    assert s.mode is SignatureMode.INVISIBLE
    assert s.incremental_update is True
    assert s.preserve_original is True
    assert s.atomic_commit is True
    assert_pus_safe_invariants(s)


def test_modern_pades_intent() -> None:
    p = modern_pades_profile(certificate_fingerprint_sha256=FP)
    s = resolve_signing_settings(p)
    assert s.pus_profile is PusProfile.MODERN_PADES
    assert s.verify_after_sign is True
    # invariants no-op for non-PUS
    assert_pus_safe_invariants(s)


def test_invariant_rejects_disabled_verify() -> None:
    p = pus_safe_profile(certificate_fingerprint_sha256=FP)
    s = resolve_signing_settings(p)
    bad = type(s)(
        profile_id=s.profile_id,
        pus_profile=s.pus_profile,
        mode=s.mode,
        verify_after_sign=False,
        atomic_commit=s.atomic_commit,
        preserve_original=s.preserve_original,
        incremental_update=s.incremental_update,
        subfilter_intent=s.subfilter_intent,
        reason=s.reason,
        location=s.location,
        filename_template=s.filename_template,
    )
    with pytest.raises(ProfileInvariantError):
        assert_pus_safe_invariants(bad)


def test_signer_rejects_bad_pus_profile(tmp_path: Path) -> None:
    from golden_signing.signing.pdf_signer import TestCertPdfSigner
    from golden_signing.signing.profiles import pus_safe_profile as mk

    engine = TestCertPdfSigner()
    profile = mk(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)
    profile.verify_after_sign = False
    profile.preserve_original = False
    src = tmp_path / "in.pdf"
    src.write_bytes(b"%PDF-1.7\nnot really")
    result = engine.sign(src, tmp_path / "out.pdf", profile=profile)
    assert result.success is False
    assert result.error_code == "PROFILE_INVARIANT"
