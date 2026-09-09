# Phase 1 — PDF/PKI + Security Review

Date: 2026-09-09
Reviewer: independent general subagent (general-4) + orchestrator remediation
Spec: `docs/compose/spec/phase-1-pdf-lab.md`
Status: **PASS with notes** (critical findings fixed before delivery)

## Verification evidence (orchestrator)

| Command | Result |
|---|---|
| `python -m pytest -q` | **PASS** exit 0 (70 tests) |
| `mypy` Phase 1 modules | **PASS** exit 0 |
| `ruff check` Phase 1 modules | **PASS** exit 0 |
| Fixture SHA-256 source | `76df3ed717a0077e4def2612005467ba8a21e095ffbe9dc076d14a150ec9b272` |
| Fixture SHA-256 signed | `11921502135884cbdcd35f366dd2ccc7176c1d22843bd1efb4668f412cd8e475` |

## Independent review conclusions

### A) Spec compliance — AC1–AC6 MET; AC7 closed by this file

| AC | Verdict |
|---|---|
| pytest 0 | MET |
| Preflight fixtures | MET (SAFE source / WARN signed / Signature1) |
| Test-cert sign+verify | MET (`intact=True valid=True`) |
| Fixture hashes unchanged | MET |
| No key/PIN/CMS leak | MET (in-memory only; private fixtures gitignored) |
| No PUS acceptance claim | MET |
| Review artifact | MET (this file) |

### B) Correctness findings

| Severity | Finding | Disposition |
|---|---|---|
| Important | verify fallback marked crypto-valid from `/Type/Sig` presence | **FIXED** — hard-fail if pyHanko validate unavailable |
| Important | output write not crash-atomic | **FIXED** — temp sibling + `os.replace` |
| Important | encrypted unit case may not exercise real `/Encrypt` | **OPEN** — recorded as known limitation; still BLOCKs unreadable input |
| Minor | `PdfSigningEngine` Protocol vs `TestCertPdfSigner` signature drift | OPEN — align when real engine adapter lands (Phase 2/3) |
| Minor | `_cms_summary` picks first chain cert | OPEN — acceptable for ECUS baseline lab |

### C) Consistency

- Module layout matches phase-1 spec map.
- Naming follows existing Phase 0 contracts/errors style.
- Control-plane updated at delivery (PROJECT_STATE / NEXT_ACTION / SESSION_HANDOFF).

## Security notes (PDF/PKI lens)

1. **Private key** — ephemeral RSA in process memory only (`test_certs.py`); never written under repo paths.
2. **Source integrity** — hash check before/after sign; refuse overwrite (`OUTPUT_CONFLICT`).
3. **No SUCCESS without verify** — post-sign pyHanko validate + ByteRange gate; output discarded on fail.
4. **ECUS baseline** — `/Adobe.PPKMS` + `/adbe.pkcs7.sha1` + ByteRange `[0, 313171, 321173, 33265]` reproduced structurally; **not** forced as Golden Signing default SubFilter.
5. **PUS claim** — none. Status remains `TECHNICALLY READY / PUS REAL-WORLD VALIDATION PENDING`.

## Recommended next action

Start Phase 2 token abstraction only after user accepts this Phase 1 delivery. Do not claim PUS compatibility without real upload test.
