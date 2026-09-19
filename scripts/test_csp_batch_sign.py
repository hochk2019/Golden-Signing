from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, r"E:\GPT\Golden Signing\src")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OUT = Path(r"E:\GPT\Golden Signing\scripts\csp_batch_test_out.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(msg)
    print(msg)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    from golden_signing.certificate.windows_store import list_windows_my_certificates
    from golden_signing.signing.windows_csp_signer import (
        clear_csp_cache,
        csp_sign_digest,
        load_store_der_by_serial,
    )

    store = list_windows_my_certificates()
    log(f"store certs: {len(store)}")
    target = None
    for c in store:
        log(f"  serial={c.serial} pk={c.has_private_key} {c.subject[:70]}")
        if c.has_private_key and "HOANG" in c.subject.upper() or (
            c.has_private_key and "TI" in c.subject and "V" in c.subject
        ):
            target = c
    if target is None:
        for c in store:
            if c.has_private_key:
                target = c
                break
    if target is None:
        log("NO store cert with private key")
        return
    serial = target.serial
    log(f"using serial={serial} {target.subject[:60]}")
    if not load_store_der_by_serial(serial):
        log("DER load failed")
        return
    clear_csp_cache()
    digests = [hashlib.sha256(f"gs-batch-{i}".encode()).digest() for i in range(3)]
    sigs = []
    for i, d in enumerate(digests):
        try:
            sig = csp_sign_digest(d, serial)
            sigs.append(len(sig))
            log(f"sign[{i}] OK len={len(sig)} cache={serial in __import__('golden_signing.signing.windows_csp_signer', fromlist=['_CSP_PROV'])._CSP_PROV}")
        except Exception as e:  # noqa: BLE001
            log(f"sign[{i}] FAIL {e}")
    log(f"result {len(sigs)}/3 ok lengths={sigs}")
    log(
        "PIN_count_estimate: vendor UI once per PowerShell/CAPI unlock; "
        "Python caches CAPI provider after first acquire"
    )


if __name__ == "__main__":
    main()
