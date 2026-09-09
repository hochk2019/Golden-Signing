"""PKCS#11 library discovery (Phase 2). Never loads the library."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

__all__ = ["ENV_PKCS11", "discover_pkcs11_libraries"]

ENV_PKCS11 = "GOLDEN_SIGNING_PKCS11"

# Well-known Windows middleware locations (existence-checked only).
_DEFAULT_RELATIVE: tuple[str, ...] = (
    r"OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"OpenSC Project\OpenSC\pkcs11\opensc-pkcs11-x64.dll",
    r"Athena\ASECard\pkcs11.dll",
    r"SafeNet\Authentication\PKCS11\epkcs11.dll",
    r"SafeNet\SoftSafeNet\pkcs11.dll",
)

_SYSTEM32_NAMES: tuple[str, ...] = (
    "opensc-pkcs11.dll",
    "eps2003csp11.dll",
    "aetpkss1.dll",
    "eTPKCS11.dll",
    "PKCS11.dll",
)


def _split_env(value: str) -> list[Path]:
    parts = value.replace(",", ";").split(";")
    return [Path(p.strip()) for p in parts if p.strip()]


def _program_files_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        raw = os.environ.get(key)
        if raw:
            roots.append(Path(raw))
    return roots


def discover_pkcs11_libraries(
    *,
    extra_roots: Iterable[Path] | None = None,
    env: dict[str, str] | None = None,
) -> list[Path]:
    """Return existing PKCS#11 DLL candidates. Does **not** load any library.

    Priority:
    1. ``GOLDEN_SIGNING_PKCS11`` (semicolon-separated paths)
    2. Well-known Program Files / System32 names
    3. ``extra_roots`` scanned for ``*.dll`` named like pkcs11
    """
    environ = env if env is not None else os.environ
    seen: set[Path] = set()
    ordered: list[Path] = []

    def _add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            return
        if resolved.is_file():
            seen.add(resolved)
            ordered.append(resolved)

    env_val = environ.get(ENV_PKCS11, "")
    if env_val.strip():
        for p in _split_env(env_val):
            _add(p)

    for root in _program_files_roots():
        for rel in _DEFAULT_RELATIVE:
            _add(root / rel)

    windir = Path(environ.get("SystemRoot", r"C:\Windows"))
    system32 = windir / "System32"
    for name in _SYSTEM32_NAMES:
        _add(system32 / name)

    if extra_roots:
        for root in extra_roots:
            if not root.is_dir():
                continue
            for child in root.iterdir():
                if child.is_file() and "pkcs11" in child.name.lower() and child.suffix.lower() == ".dll":
                    _add(child)

    return ordered
