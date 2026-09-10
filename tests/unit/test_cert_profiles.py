"""Unit tests for cert profile store."""

from __future__ import annotations

from pathlib import Path

from golden_signing.storage.cert_profiles import CertProfile, CertProfileStore


def test_profile_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    store = CertProfileStore(path)
    store.upsert(
        CertProfile(
            fingerprint="ab" * 32,
            company="ABC",
            text_color_key="navy",
            show_logo=True,
            logo_path="C:/logo.png",
            show_background=True,
            signature_mode="visible",
        )
    )
    store2 = CertProfileStore(path)
    p = store2.get("ab" * 32)
    assert p is not None
    assert p.company == "ABC"
    assert p.show_logo is True
    assert p.logo_path == "C:/logo.png"


def test_missing_profile(tmp_path: Path) -> None:
    store = CertProfileStore(tmp_path / "p.json")
    assert store.get("ff" * 32) is None
    assert store.all() == []
