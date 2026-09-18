#!/usr/bin/env python3
"""Run on CUSTOMER PC after Golden Sign Token error. No PIN required.

Checks: PKCS#11 DLL bitness, token presence, Windows My store certs.
Output: token_diag_report.txt next to this script or in TEMP.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

# Prefer installed app path if frozen; else repo src
if getattr(sys, "frozen", False):
    pass
else:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("token_diag_report.txt")
lines: list[str] = []


def log(msg: str = "") -> None:
    lines.append(msg)
    print(msg)


def main() -> int:
    log(f"Golden Sign token diagnostic {datetime.now().isoformat()}")
    log(f"Python {sys.version}  64bit={sys.maxsize > 2**32}")
    try:
        from golden_signing.certificate.catalog import collect_display_certificates
        from golden_signing.certificate.windows_store import (
            certificate_is_signing_capable,
            list_windows_my_certificates,
        )
        from golden_signing.signing.token_pdf_signer import TokenPdfSigner
        from golden_signing.token.discovery import (
            discover_pkcs11_libraries,
            pe_machine_label,
        )

        compat = discover_pkcs11_libraries()
        all_dlls = discover_pkcs11_libraries(include_incompatible=True)
        log("\n=== PKCS#11 DLL (compatible with Golden Sign) ===")
        if not compat:
            log("(NONE) — Golden Sign cannot open token until x64 middleware is installed")
        for p in compat:
            log(f"  [{pe_machine_label(p)}] {p}")
        log("\n=== PKCS#11 DLL (all found, incl. wrong bitness) ===")
        for p in all_dlls:
            tag = "OK" if p in compat else "SKIP"
            log(f"  [{tag} {pe_machine_label(p)}] {p}")

        log("\n=== Probe each compatible DLL (no PIN) ===")
        for p in compat:
            try:
                certs = TokenPdfSigner.list_certificates(p)
                log(f"  {p.name}: {len(certs)} cert(s)")
                for c in certs:
                    log(f"    serial={c.serial} subject={c.subject[:80]}")
            except Exception as e:  # noqa: BLE001
                log(f"  {p.name}: FAIL {e}")

        log("\n=== Windows certmgr My (certutil hidden) ===")
        store = list_windows_my_certificates()
        log(f"  count={len(store)}")
        for c in store:
            log(
                f"  pk={c.has_private_key} sign={certificate_is_signing_capable(c)} "
                f"after={c.not_valid_after} serial={c.serial}"
            )
            log(f"    {c.subject[:100]}")

        log("\n=== Display certs (what Golden Sign picker would show) ===")
        disp = collect_display_certificates(use_cache=False)
        if not disp:
            log("  (empty)")
        for c in disp:
            log(f"  [{c.backend}] serial={c.serial} {c.subject[:80]}")
            log(f"    token_label={c.token_label} after={c.not_valid_after}")

        log("\n=== Interpreting error Chi tiết None ===")
        log("  Means: no compatible PKCS#11 DLL OR open_session never raised.")
        log("  Fix: install CA2/ECA/VNPT **x64** middleware; plug token; Quét lại token.")
        log("  DLL in SysWOW64 / TSD\\ECUS_EX4 are usually 32-bit — not for Golden Sign x64.")
    except Exception:  # noqa: BLE001
        log(traceback.format_exc())
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
