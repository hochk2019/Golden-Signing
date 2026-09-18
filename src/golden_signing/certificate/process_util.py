"""Hidden subprocess helpers — never flash a console window on Windows."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

CREATE_NO_WINDOW = 0x08000000


def hidden_run_kwargs() -> dict[str, Any]:
    if not sys.platform.startswith("win"):
        return {}
    return {"creationflags": CREATE_NO_WINDOW}


def run_hidden(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    kwargs.setdefault("capture_output", True)
    kwargs.update(hidden_run_kwargs())
    return subprocess.run(cmd, **kwargs)  # noqa: S603


def popen_hidden(cmd: list[str], **kwargs: Any) -> subprocess.Popen:
    kwargs.update(hidden_run_kwargs())
    return subprocess.Popen(cmd, **kwargs)  # noqa: S603
