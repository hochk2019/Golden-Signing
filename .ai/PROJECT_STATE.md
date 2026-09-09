# PROJECT STATE

Status legend: DONE | IN_PROGRESS | BLOCKED | TODO | DEFERRED

| ID | Objective | Status | Depends | Files | Tests | Evidence | Next |
|---|---|---|---|---|---|---|---|
| P0-01..10 | Research lock + scaffold | DONE | — | see Phase 0 | 7 smoke | commit 691f09f / 3e49261 | — |
| P1-01 | PDF preflight laboratory | DONE | P0 | `pdf/inspection.py` | unit+integration | pytest 70 pass | — |
| P1-02 | Sign with test certificate | DONE | P1-01 | `signing/pdf_signer.py`, `test_certs.py` | integration sign+verify | intact/valid True | — |
| P1-03 | ByteRange + structural baseline | DONE | P1-01 | `pdf/integrity.py`, `pdf/baseline.py` | unit+integration | ECUS baseline matches §2 | — |
| P1-04 | Independent review | DONE | P1-01..03 | `.ai/reviews/phase1-pdf-pki.md` | — | review PASS w/ notes | — |
| P2-01 | PKCS#11 token adapter | TODO | P1-02 | `token/pkcs11.py` | token present | user token | Phase 2 |

## Verification evidence (Phase 1)

- `pytest -q` — **70 passed**, exit 0
- `mypy` Phase 1 modules — PASS
- `ruff check` Phase 1 modules — PASS
- pyHanko **0.37.0**
- ECUS signed: `Signature1`, `/Adobe.PPKMS`, `/adbe.pkcs7.sha1`, ByteRange `[0, 313171, 321173, 33265]`
- CMS: subject CÔNG TY TNHH ICH CUBE VIỆT NAM / issuer CA2 NACENCOMM SCT; fingerprint `62003b776fa39a574904c0fc3a6cd691bde004320e4bd365a0c4f00777474cda`
- Test-cert sign+verify: `intact=True valid=True`; source fixture hashes unchanged

## Status label

`PHASE 1 PDF LABORATORY COMPLETE / PUS REAL-WORLD VALIDATION PENDING`
