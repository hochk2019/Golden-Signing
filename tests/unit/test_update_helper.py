"""v1.1.5: helper must use CREATE_NO_WINDOW so PowerShell actually runs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from golden_signing.updater.runtime import launch_update_helper, write_update_helper


def test_helper_script_has_log_and_wait(tmp_path: Path) -> None:
    upd = tmp_path / "updates"
    install = tmp_path / "Programs" / "GoldenSign"
    staged = upd / "staged"
    ps1 = write_update_helper(upd, install, staged)
    text = ps1.read_text(encoding="utf-8")
    assert "apply_update.log" in text or "Log" in text
    assert "Get-Process" in text
    assert "Copy-Item" in text


def test_launch_uses_create_no_window(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Regression: DETACHED_PROCESS made powershell exit 0 without running -File."""
    captured: dict[str, object] = {}

    def fake_popen(cmd, **kwargs):  # noqa: ANN001, ANN202
        captured["cmd"] = cmd
        captured["flags"] = kwargs.get("creationflags")
        class P:
            pid = 123
            def poll(self): return 0
        return P()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    script = tmp_path / "apply_update.ps1"
    script.write_text("exit 0", encoding="utf-8")
    launch_update_helper(script)
    assert "powershell.exe" in captured["cmd"][0]
    assert captured["flags"] == 0x08000000  # CREATE_NO_WINDOW
    if sys.platform.startswith("win"):
        assert captured["flags"] != (0x00000008 | 0x00000200)  # not DETACHED_PROCESS
