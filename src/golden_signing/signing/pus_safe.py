"""PUS Safe / Modern PAdES effective settings (spec §5.4, §12, ADR-8).

Never hard-code ECUS packaging. Profile-controlled SubFilter intent only.
"""

from __future__ import annotations

from dataclasses import dataclass

from golden_signing.signing.contracts import (
    PusProfile,
    SignatureMode,
    SigningProfile,
)
from golden_signing.signing.exceptions import GoldenSigningError

__all__ = [
    "EffectiveSigningSettings",
    "SUBFILTER_MODERN",
    "SUBFILTER_PUS_COMPAT",
    "assert_pus_safe_invariants",
    "resolve_signing_settings",
]

SUBFILTER_MODERN = "adbe.pkcs7.detached"
SUBFILTER_PUS_COMPAT = "adbe.pkcs7.sha1"


class ProfileInvariantError(GoldenSigningError):
    code = "PROFILE_INVARIANT"


@dataclass(frozen=True, slots=True)
class EffectiveSigningSettings:
    profile_id: str
    pus_profile: PusProfile
    mode: SignatureMode
    verify_after_sign: bool
    atomic_commit: bool
    preserve_original: bool
    incremental_update: bool
    subfilter_intent: str
    reason: str | None
    location: str | None
    filename_template: str


def resolve_signing_settings(profile: SigningProfile) -> EffectiveSigningSettings:
    """Resolve engine settings from a SigningProfile.

    PUS Safe forces verify_after_sign=True and invisible default unless profile
    already chose a non-default mode that the user explicitly set (mode field).
    """
    is_pus = profile.pus_profile is PusProfile.PUS_SAFE
    verify = True if is_pus else bool(profile.verify_after_sign)
    mode = profile.mode
    if is_pus and mode is SignatureMode.VISIBLE:
        # Visible is allowed only when explicitly chosen on the profile object.
        pass
    subfilter = SUBFILTER_PUS_COMPAT if is_pus else SUBFILTER_MODERN
    # Intent only — engine may still emit modern packaging until PUS-validated.
    if is_pus:
        subfilter = "profile-controlled"  # do not force sha1 until PUS lab proves it
    return EffectiveSigningSettings(
        profile_id=profile.id,
        pus_profile=profile.pus_profile,
        mode=mode,
        verify_after_sign=verify,
        atomic_commit=bool(profile.atomic_commit),
        preserve_original=bool(profile.preserve_original),
        incremental_update=True,
        subfilter_intent=subfilter,
        reason=profile.reason,
        location=profile.location,
        filename_template=profile.filename_template,
    )


def assert_pus_safe_invariants(settings: EffectiveSigningSettings) -> None:
    """Hard invariants for PUS Safe (spec §12, §49)."""
    if settings.pus_profile is not PusProfile.PUS_SAFE:
        return
    if not settings.verify_after_sign:
        raise ProfileInvariantError("PUS Safe requires verify_after_sign=True")
    if not settings.preserve_original:
        raise ProfileInvariantError("PUS Safe requires preserve_original=True")
    if not settings.atomic_commit:
        raise ProfileInvariantError("PUS Safe requires atomic_commit=True")
    if not settings.incremental_update:
        raise ProfileInvariantError("PUS Safe requires incremental_update=True")
