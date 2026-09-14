"""Update helper script: waits for app exit then swaps install dir."""

from __future__ import annotations

from pathlib import Path

from golden_signing.updater.runtime import write_update_helper


def test_helper_script_contents(tmp_path: Path) -> None:
    upd = tmp_path / "updates"
    install = tmp_path / "Programs" / "GoldenSign"
    staged = upd / "staged-v1.1.3"
    ps1 = write_update_helper(upd, install, staged)
    text = ps1.read_text(encoding="utf-8")
    assert "Get-Process" in text
    assert "Rename-Item" in text
    assert "Copy-Item" in text
    assert "Start-Process" in text
    assert str(install).replace("\\", "/") in text.replace("\\", "/") or str(install) in text
    assert ps1.is_file()
