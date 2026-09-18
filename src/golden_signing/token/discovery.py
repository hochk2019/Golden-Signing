"""PKCS#11 library discovery (Phase 2). Never loads the library."""

from __future__ import annotations

import os
import struct
import sys
from collections.abc import Iterable
from pathlib import Path

__all__ = [
    "ENV_PKCS11",
    "discover_pkcs11_libraries",
    "pe_machine",
    "is_compatible_pkcs11_dll",
]

ENV_PKCS11 = "GOLDEN_SIGNING_PKCS11"

PE_MACHINE_I386 = 0x014C
PE_MACHINE_AMD64 = 0x8664
PE_MACHINE_ARM64 = 0xAA64

# Well-known Windows middleware locations (existence-checked only).
_DEFAULT_RELATIVE: tuple[str, ...] = (
    r"OpenSC Project\OpenSC\pkcs11\opensc-pkcs11-x64.dll",
    r"OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"Athena\ASECard\pkcs11.dll",
    r"SafeNet\Authentication\PKCS11\epkcs11.dll",
    r"SafeNet\SoftSafeNet\pkcs11.dll",
    # Prefer non-(x86) vendor paths first when present
    r"VNPT\VNPT-CA\vnpt-ca_p11_v10.dll",
    r"FPT\FPT_CA\fptca_v4.dll",
    r"CA2\PKCS11\CA2_csp11.dll",
    r"BKAV\BKAVCA\BkavCA_P11.dll",
    r"ViettelCA\viettel-ca_p11.dll",
    r"ECA\PKCS11\eca_csp11_v1.dll",
    # Often 32-bit ECUS middleware — only used if PE matches process
    r"TSD\ECUS_EX4\vnpt-ca_csp11.dll",
    r"TSD\ECUS_EX4\CA2_csp11.dll",
    r"TSD\ECUS_EX4\ostc1_csp11.dll",
    r"TSD\ECUS_K4\vnpt-ca_csp11.dll",
    r"TSD\TokenManager\pkcs11.dll",
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
    "CA2_csp11_s.dll",
    "ca2_ace_csp11.dll",
    "ca2_ace_csp11_s.dll",
    "ostc1_csp11.dll",
    "ostc1_csp11_s.dll",
    "BkavCA_P11.dll",
    "viettel-ca_p11.dll",
)

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
    # 64-bit Program Files first (more likely to host x64 middleware)
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        raw = os.environ.get(key)
        if raw:
            roots.append(Path(raw))
    return roots


def _looks_like_pkcs11_dll(name: str) -> bool:
    low = name.lower()
    if not low.endswith(".dll"):
        return False
    # Vendor helper modules (CA2_csp11_s.dll) are not full PKCS#11 providers
    if low.endswith("_s.dll"):
        return False
    return any(h in low for h in _DLL_NAME_HINTS)


def process_is_64bit() -> bool:
    return sys.maxsize > 2**32


def pe_machine(path: Path) -> int | None:
    """Return PE machine field (0x8664 x64, 0x14c x86) or None if unreadable."""
    try:
        with Path(path).open("rb") as f:
            if f.read(2) != b"MZ":
                return None
            f.seek(0x3C)
            e_lfanew = struct.unpack("<I", f.read(4))[0]
            if e_lfanew <= 0 or e_lfanew > 0x10000:
                return None
            f.seek(e_lfanew)
            if f.read(4) != b"PE\x00\x00":
                return None
            return struct.unpack("<H", f.read(2))[0]
    except Exception:  # noqa: BLE001
        return None


def is_compatible_pkcs11_dll(path: Path) -> bool:
    """True if this PKCS#11 DLL can load in the current process bitness."""
    machine = pe_machine(path)
    if machine is None:
        return True  # unknown — try load later
    if process_is_64bit():
        return machine != PE_MACHINE_I386
    return machine == PE_MACHINE_I386


def pe_machine_label(path: Path) -> str:
    m = pe_machine(path)
    if m == PE_MACHINE_AMD64:
        return "x64"
    if m == PE_MACHINE_I386:
        return "x86"
    if m == PE_MACHINE_ARM64:
        return "arm64"
    return "unknown"


def discover_pkcs11_libraries(
    *,
    extra_roots: Iterable[Path] | None = None,
    env: dict[str, str] | None = None,
    include_incompatible: bool = False,
) -> list[Path]:
    """Return existing PKCS#11 DLL candidates. Does **not** load any library.

    Compatible DLLs (same bitness as Golden Sign process) come first.
    Incompatible (e.g. 32-bit middleware vs 64-bit app) are dropped unless
    ``include_incompatible=True`` (used for diagnostics).
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
        if resolved.name.lower().endswith("_s.dll"):
            return
        if resolved.is_file():
            seen.add(resolved)
            ordered.append(resolved)

    env_val = environ.get(ENV_PKCS11, "")
    if env_val.strip():
        for p in _split_env(env_val):
            _add(p)

    # System32 = native 64-bit on 64-bit Windows — best for this app
    windir = Path(environ.get("SystemRoot", r"C:\Windows"))
    system32 = windir / "System32"
    for name in _SYSTEM32_NAMES:
        _add(system32 / name)

    for root in _program_files_roots():
        for rel in _DEFAULT_RELATIVE:
            _add(root / rel)
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

    # SysWOW64 = 32-bit system DLLs on 64-bit Windows — last resort only
    syswow = windir / "SysWOW64"
    for name in _SYSTEM32_NAMES:
        _add(syswow / name)

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

    compatible = [p for p in ordered if is_compatible_pkcs11_dll(p)]
    incompatible = [p for p in ordered if p not in compatible]
    if include_incompatible:
        return compatible + incompatible
    return compatible
