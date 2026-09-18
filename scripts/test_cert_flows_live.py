#!/usr/bin/env python3
"""Live check: cert scan / store enum / add-file path — assert no PowerShell spawn."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\GPT\Golden Signing\src")


def _ps_processes() -> set[int]:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq powershell.exe", "/FO", "CSV", "/NH"],
            text=True,
            errors="replace",
        )
    except Exception as e:  # noqa: BLE001
        print("tasklist fail", e)
        return set()
    pids = set()
    for line in out.splitlines():
        if "powershell" in line.lower():
            parts = line.replace('"', "").split(",")
            if len(parts) >= 2:
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    pass
    return pids


def main() -> int:
    before = _ps_processes()
    print("powershell before:", before)

    t0 = time.perf_counter()
    from golden_signing.certificate.windows_store import list_windows_my_certificates
    from golden_signing.certificate.catalog import (
        clear_certificate_cache,
        collect_display_certificates,
    )
    from golden_signing.token.discovery import discover_pkcs11_libraries
    from golden_signing.certificate.windows_store import certificate_is_signing_capable

    store = list_windows_my_certificates()
    t1 = time.perf_counter()
    print(f"store certs: {len(store)} in {t1-t0:.3f}s")
    for c in store:
        print(
            f"  store pk={c.has_private_key} sign={certificate_is_signing_capable(c)} "
            f"eku={c.eku_oids} {c.subject[:70]}"
        )

    mid = _ps_processes()
    print("powershell after store enum:", mid, "NEW", mid - before)

    clear_certificate_cache()
    t2 = time.perf_counter()
    dlls = discover_pkcs11_libraries()
    certs = collect_display_certificates(use_cache=False)
    t3 = time.perf_counter()
    print(f"pkcs11 dlls={len(dlls)} display_certs={len(certs)} in {t3-t2:.3f}s")
    for d in dlls[:12]:
        print("  dll", d)
    for c in certs:
        print(f"  display [{c.backend}] {c.subject[:60]} after={c.not_valid_after[:10]}")

    t4 = time.perf_counter()
    certs2 = collect_display_certificates(use_cache=True)
    t5 = time.perf_counter()
    print(f"cached display={len(certs2)} in {t5-t4:.4f}s")

    after = _ps_processes()
    print("powershell after all scans:", after, "NEW", after - before)

    # add-file simulation: no cert scan
    pdf = Path(r"E:\GPT\Golden Signing\tests\fixtures\private\ecus_source.pdf")
    if not pdf.exists():
        pdf = Path(r"E:\GPT\Golden Signing\Golden_Sign_ECUSSign\analysis\live_captures\3_live_signed_01_336969_JYE-VN-P-26-180.pdf")
    print("add-file sample exists:", pdf.exists(), pdf)
    t6 = time.perf_counter()
    if pdf.exists():
        data = pdf.read_bytes()[:16]
        print("read head", data[:8])
    t7 = time.perf_counter()
    print(f"file add path {t7-t6:.4f}s (no cert scan expected)")

    new_ps = _ps_processes() - before
    print("RESULT new_powershell_pids:", new_ps or "NONE")
    print("PASS no powershell" if not new_ps else "FAIL powershell spawned")
    return 0 if not new_ps else 1


if __name__ == "__main__":
    raise SystemExit(main())
