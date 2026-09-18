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
    # Vietnamese CA middleware (ECUS / TokenManager installs)
    r"TSD\ECUS_EX4\vnpt-ca_csp11.dll",
    r"TSD\ECUS_EX4\CA2_csp11.dll",
    r"TSD\ECUS_EX4\ostc1_csp11.dll",
    r"TSD\ECUS_K4\vnpt-ca_csp11.dll",
    r"TSD\TokenManager\pkcs11.dll",
    r"VNPT\VNPT-CA\vnpt-ca_p11_v10.dll",
    r"FPT\FPT_CA\fptca_v4.dll",
    r"CA2\PKCS11\CA2_csp11.dll",
    r"BKAV\BKAVCA\BkavCA_P11.dll",
    r"ViettelCA\viettel-ca_p11.dll",
)

_SYSTEM32_NAMES: tuple[str, ...] = (
    "eca_csp11_v1.dll",
    "eca_csp11.dll",
    "opensc-pkcs11.dll",
    "eps2003csp11.dll",
    "aetpkss1.dll",
    "eTPKCS11.dll",
    "PKCS11.dll",
    "vnptca_p11_v10.dll",
    "vnpt-ca_csp11.dll",
    "fptca_v4.dll",
    "CA2_csp11.dll",
    "ostc1_csp11.dll",
    "ostc1_csp11_s.dll",
    "BkavCA_P11.dll",
    "viettel-ca_p11.dll",
)

# Filename fragments used when scanning Program Files / vendor folders.
_DLL_NAME_HINTS: tuple[str, ...] = (
    "pkcs11",
    "csp11",
    "p11",
    "epkcs11",
    "aetpkss1",
)

_SCAN_DIR_HINTS: tuple[str, ...] = (
    "TSD",
    "ECUS",
    "VNPT",
    "FPT",
    "CA2",
    "BKAV",
    "Viettel",
    "ECA",
    "TokenManager",
    "SafeNet",
    "OpenSC",
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


def _looks_like_pkcs11_dll(name: str) -> bool:
    low = name.lower()
    if not low.endswith(".dll"):
        return False
    return any(h in low for h in _DLL_NAME_HINTS)


def discover_pkcs11_libraries(
    *,
    extra_roots: Iterable[Path] | None = None,
    env: dict[str, str] | None = None,
) -> list[Path]:
    """Return existing PKCS#11 DLL candidates. Does **not** load any library.

    Priority:
    1. ``GOLDEN_SIGNING_PKCS11`` (semicolon-separated paths)
    2. Well-known Program Files / System32 / SysWOW64 names
    3. Vendor folders under Program Files (TSD/ECUS/VNPT/…)
    4. ``extra_roots`` scanned for pkcs11-like DLLs
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
        # Shallow vendor folder scan (depth 2–3)
        try:
            if root.is_dir():
                for child in root.iterdir():
                    if not child.is_dir():
                        continue
                    name_l = child.name.lower()
                    if not any(h.lower() in name_l for h in _SCAN_DIR_HINTS):
                        continue
                    for sub in (child, *list(child.iterdir())[:20]):
                        if not sub.is_dir():
                            continue
                        try:
                            for dll in sub.iterdir():
                                if dll.is_file() and _looks_like_pkcs11_dll(dll.name):
                                    _add(dll)
                        except OSError:
                            continue
        except OSError:
            pass

    windir = Path(environ.get("SystemRoot", r"C:\Windows"))
    for sub in ("System32", "SysWOW64"):
        system_dir = windir / sub
        for name in _SYSTEM32_NAMES:
            _add(system_dir / name)

    if extra_roots:
        for root in extra_roots:
            if not root.is_dir():
                continue
            try:
                children = list(root.iterdir())
            except OSError:
                continue
            for child in children:
                if child.is_file() and _looks_like_pkcs11_dll(child.name):
                    _add(child)

    return ordered
