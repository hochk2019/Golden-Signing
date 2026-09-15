"""Packaging script regressions."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_inno_deletes_old_internal_payload_before_install() -> None:
    script = (ROOT / "packaging" / "golden_sign.iss").read_text(encoding="utf-8")
    assert '[InstallDelete]' in script
    assert 'Name: "{app}\\_internal"' in script
    assert 'Name: "{app}\\GoldenSign.exe"' in script


def test_portable_installer_deletes_old_internal_payload_before_copy() -> None:
    script = (ROOT / "packaging" / "install.ps1").read_text(encoding="utf-8")
    assert 'Join-Path $InstallDir "_internal"' in script
    assert "Remove-Item -LiteralPath" in script
