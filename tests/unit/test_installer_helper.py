"""v1.1.10: installer helper must not pass /DIR with embedded quotes."""

from __future__ import annotations

from pathlib import Path

from golden_signing.updater.runtime import write_installer_helper


def test_installer_helper_no_dir_quotes(tmp_path: Path) -> None:
    upd = tmp_path / "updates"
    upd.mkdir(parents=True, exist_ok=True)
    install = tmp_path / "Programs" / "GoldenSign"
    installer = upd / "installer-v1.1.10.exe"
    installer.write_bytes(b"MZ")
    ps1 = write_installer_helper(upd, install, installer)
    text = ps1.read_text(encoding="utf-8")
    # Regression: embedded /DIR="..." caused Inno exit code 3
    assert '/DIR="' not in text
    assert "/DIR=" not in text
    # Still uses silent flags
    assert "/VERYSILENT" in text
    assert "/SUPPRESSMSGBOXES" in text
    assert "Start-Process" in text
    assert "relaunched" in text
