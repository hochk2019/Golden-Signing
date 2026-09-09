"""Signing profile presets as data (spec §5.4, §12, ADR-8).

PUS-Compatibility vs Modern-PAdES stay config profiles — not hard-coded constants.
"""

from __future__ import annotations

from golden_signing.signing.contracts import (
    PusProfile,
    SignatureMode,
    SigningProfile,
)

# SubFilter intent labels for later engine selection (Phase 1 records actual value).
SUBFILTER_MODERN = "adbe.pkcs7.detached"
SUBFILTER_PUS_COMPAT = "adbe.pkcs7.sha1"


def pus_safe_profile(
    *,
    certificate_fingerprint_sha256: str,
    profile_id: str = "pus-safe-default",
    name: str = "PUS Safe",
) -> SigningProfile:
    """PUS Safe: invisible, preserve content, verify after sign, never overwrite."""
    return SigningProfile(
        id=profile_id,
        name=name,
        certificate_fingerprint_sha256=certificate_fingerprint_sha256,
        mode=SignatureMode.INVISIBLE,
        pus_profile=PusProfile.PUS_SAFE,
        verify_after_sign=True,
        atomic_commit=True,
        preserve_original=True,
        filename_template="{original_name}_signed.pdf",
    )


def modern_pades_profile(
    *,
    certificate_fingerprint_sha256: str,
    profile_id: str = "modern-pades-default",
    name: str = "Modern PAdES",
) -> SigningProfile:
    """Modern PAdES path; visible mode is caller-controlled."""
    return SigningProfile(
        id=profile_id,
        name=name,
        certificate_fingerprint_sha256=certificate_fingerprint_sha256,
        mode=SignatureMode.INVISIBLE,
        pus_profile=PusProfile.MODERN_PADES,
        verify_after_sign=True,
        atomic_commit=True,
        preserve_original=True,
        filename_template="{original_name}_signed.pdf",
    )


def profile_for_pus_kind(
    kind: PusProfile,
    *,
    certificate_fingerprint_sha256: str,
) -> SigningProfile:
    if kind is PusProfile.PUS_SAFE:
        return pus_safe_profile(certificate_fingerprint_sha256=certificate_fingerprint_sha256)
    if kind is PusProfile.MODERN_PADES:
        return modern_pades_profile(certificate_fingerprint_sha256=certificate_fingerprint_sha256)
    raise ValueError(f"unsupported pus profile kind: {kind}")
