"""Diagnostics bundle export (redacted)."""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

__all__ = ["build_diagnostics", "export_diagnostics"]


def build_diagnostics() -> dict[str, Any]:
    info: dict[str, Any] = {
        "app": "Golden Signing",
        "version": "0.1.0a0",
        "generated_at": time.time(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
        },
        "packages": {},
        "pkcs11_dlls": [],
        "notes": [
            "No PIN, private keys, or PDF contents included.",
        ],
    }
    try:
        import importlib.metadata as md

        for name in ("pyHanko", "pypdfium2", "cryptography", "PySide6", "python-pkcs11"):
            try:
                info["packages"][name] = md.version(name)
            except Exception:  # noqa: BLE001
                info["packages"][name] = "n/a"
    except Exception:  # noqa: BLE001
        pass
    try:
        from golden_signing.token.discovery import discover_pkcs11_libraries

        info["pkcs11_dlls"] = [str(p) for p in discover_pkcs11_libraries()[:10]]
    except Exception:  # noqa: BLE001
        pass
    try:
        from golden_signing.signing.appearance import resolve_vietnamese_font

        info["system_font"] = resolve_vietnamese_font()
    except Exception:  # noqa: BLE001
        pass
    return info


def export_diagnostics(dest_dir: Path) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"golden-signing-diagnostics-{int(time.time())}.json"
    out.write_text(json.dumps(build_diagnostics(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out
