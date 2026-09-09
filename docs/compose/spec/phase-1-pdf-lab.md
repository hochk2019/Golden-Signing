---
feature: phase-1-pdf-lab
status: delivered
updated: 2026-09-09
branch: main
commits: 3e49261..HEAD # Phase 1 delivery on main; see git log
---

# Phase 1 — PDF Laboratory

## Report

**What was built** — A working PDF laboratory on `main`: preflight classification (`SAFE`/`WARN`/`BLOCK`) for golden fixtures, ByteRange extract/validate and content-range hashes, structural baseline compare against the ECUS-signed sample (page count, AcroForm, `Signature1`, `/Adobe.PPKMS`, `/adbe.pkcs7.sha1`, ByteRange `[0, 313171, 321173, 33265]`, CMS subject/issuer/fingerprint), ephemeral in-memory RSA test certificates, and a pyHanko-backed `TestCertPdfSigner` that signs a copy of `ecus_source.pdf`, verifies cryptographic integrity + ByteRange, refuses source overwrite, and discards output if verify fails. Profile presets (`PUS Safe`, `Modern PAdES`) are data-only; ECUS SHA-1 packaging is recorded, not forced.

**Verification** — `python -m pytest -q` **70 passed** exit 0; `mypy` Phase 1 modules exit 0; `ruff check` Phase 1 modules exit 0; fixture SHA-256s unchanged; independent review PASS with notes (`.ai/reviews/phase1-pdf-pki.md`); sign+verify evidence `intact=True valid=True`.

**Journey log**
1. Multi-agent T2/T3/T5 subagents wrote code then failed with APIError on wrap-up; orchestrator verified and finished in-session (same pattern as Phase 0 research).
2. Independent review subagent succeeded and forced two Important fixes: verify hard-fail (no `/Type/Sig` crypto fallback) and temp+`os.replace` atomic promote.
3. pyHanko `in_place=True` on a read-only input stream raised `io.UnsupportedOperation: write`; switched to separate output stream.
4. ECUS baseline fingerprint matches spec §2.3 exactly — do not “fix” fixture hashes.
5. Status remains `PHASE 1 PDF LABORATORY COMPLETE / PUS REAL-WORLD VALIDATION PENDING`.

## [S1] Problem

Golden Signing Phase 0 locked the stack and domain contracts but has no working PDF inspection or signing path. The product cannot yet prove it can produce a cryptographically valid signed PDF that preserves page content and can later be validated against PUS/ECUS baselines. Spec §30 Phase 1 and `.ai/NEXT_ACTION.md` require a laboratory that:

- parses the two private golden fixtures;
- detects existing signatures / ByteRange / CMS on the ECUS-signed sample;
- implements preflight (`SAFE` / `WARN` / `BLOCK`);
- signs `ecus_source.pdf` with a **test certificate** (not USB token);
- verifies the signed output;
- compares structure against the ECUS baseline without claiming PUS acceptance.

Without this, later token, batch, and UI work has no trustworthy crypto foundation.

## [S2] Design

### Workspace override

User chose **continue on `main`** at `E:\GPT\Golden Signing` (no linked worktree). Record this as an explicit override of compose-next default worktree and D-005 preference.

### Skill composition

- Process: `compose-next` (this document)
- Implementation: `test-driven-development`, `systematic-debugging`, `verification-before-completion`
- Parallelism: `subagent-driven-development` / actor subagents with disjoint file sets; commits stay with orchestrator
- `memory-systems` **out of scope** for this phase (agent-memory architecture, not PDF lab)

### Architecture (unchanged from ADR)

```
UI (not in this phase)
  -> Application services
    -> Domain contracts (extend PreflightResult; keep Protocols)
      -> Infrastructure (pyHanko, pypdfium2, cryptography)
```

Signing Core must not import UI. No PKCS#11 token I/O in Phase 1.

### Module layout for this phase

```
src/golden_signing/
  pdf/
    inspection.py      # preflight: header, pages, encryption, AcroForm, signatures
    integrity.py       # ByteRange extract/validate, file hash helpers
    baseline.py        # structural compare source vs signed / golden output
  certificate/
    models.py          # thin re-exports / helpers around CertificateInfo if needed
  signing/
    test_certs.py      # ephemeral RSA test certificate generation (lab only)
    pdf_signer.py      # pyHanko-backed PdfSigningEngine implementation (test-cert path)
    profiles.py        # PUS_SAFE / MODERN_PADES profile presets as data
tests/
  unit/test_pdf_inspection.py
  unit/test_pdf_integrity.py
  unit/test_profiles.py
  integration/test_sign_testcert.py
  integration/test_golden_baseline.py
```

### Preflight contract (extend, do not break)

Extend `PreflightResult` in `signing/contracts.py` with optional fields (backward compatible defaults):

- `pdf_version: str | None`
- `page_count: int` (already present)
- `encrypted: bool` (already present)
- `file_size_bytes: int`
- `writable: bool`
- `existing_signatures: list[str]` (already present; fill with field names)
- `has_acroform: bool`
- `incremental_revisions: int`
- `warnings: list[str]` (already present)
- `errors: list[str]` (already present)

Levels (spec §9):

| Level | Meaning |
|---|---|
| `SAFE` | readable, not encrypted, signable |
| `WARN` | readable but has existing signature / AcroForm / odd metadata — sign may append revision |
| `BLOCK` | unreadable, encrypted without permission, or not a PDF |

### Structural baseline (ECUS compare — not byte-identity)

Compare and record (spec §11.3):

- page count
- `/AcroForm` presence and `/SigFlags`
- signature field names / `/SubFilter`
- `/ByteRange` shape (4 integers; covers file except `/Contents` hex)
- CMS parse: subject, issuer, serial, fingerprint SHA-256, digest algorithm
- Producer/Creator metadata delta
- page content stream hash equality for unsigned pages (content preservation)

**Do not** require byte-for-byte match with ECUS. **Do not** copy ECUS `/M` timestamp `D:20100101000000+07'00'`.

### Signing path (test certificate only)

1. Generate ephemeral RSA-2048 self-signed cert in-memory / temp (lab only; never persist private key to repo or logs).
2. Sign a **copy** of `ecus_source.pdf` via pyHanko to a temp/output path under `tests/output/` or pytest tmp_path.
3. Profile: `PUS_SAFE` defaults — invisible signature, incremental update, post-sign verify on, no overwrite of source.
4. SubFilter: start with pyHanko default modern path (`adbe.pkcs7.detached` / PAdES as library chooses). Record actual SubFilter in baseline report. Do **not** force `adbe.pkcs7.sha1` until a later PUS-Compatibility profile is proven (spec §2.4, N-005).
5. After sign: re-open output, verify cryptographic validity, ByteRange integrity, certificate extractable.
6. Source fixture SHA-256 must be unchanged.

### Atomic output

Reuse `security/integrity.atomic_write_bytes` or pyHanko write-to-temp then `os.replace`. Never leave a “signed” file if verify fails (spec §5.3, §38).

### Logging / secrets

- Never log PIN, private key material, or full CMS blobs at Normal level.
- Test cert private keys are ephemeral and discarded.

### Out of scope for claims

- No “PUS compatible” claim.
- No USB token.
- No UI.
- Status label remains: `TECHNICALLY READY / PUS REAL-WORLD VALIDATION PENDING` after Phase 1.

### Parallel implementation plan

| Lane | Owner | Files | Depends |
|---|---|---|---|
| L1 Preflight | subagent A | `pdf/inspection.py`, tests unit inspection | — |
| L2 Integrity/baseline | subagent B | `pdf/integrity.py`, `pdf/baseline.py`, tests | fixtures present |
| L3 Sign+verify | subagent C | `signing/test_certs.py`, `signing/pdf_signer.py`, `signing/profiles.py`, integration tests | L1 contracts frozen; pyHanko |
| Orchestrator | main session | contracts extend, spec updates, `.ai/` state, commits, review dispatch | all lanes |

Commits remain with the orchestrator on `main`.

## [S3] Out of Scope

- PySide6 / any UI
- PKCS#11 / Windows CSP token adapters
- Real PUS upload or “PUS accepted” claim
- Batch queue UI / worker pool (batch state machine stays data-only)
- Branding mark/PNG/ICO variants (defer to pre-UI)
- Remote updater, installer, code signing
- Forcing ECUS `adbe.pkcs7.sha1` as default
- Editing `Golden Signing v1.2.0.md`
- Committing private golden PDFs

## Tasks

- [x] T1: Freeze/extend PreflightResult + profile presets — acceptance: contracts import clean; unit tests for profile defaults (covers: S2)
- [x] T2: Implement `pdf/inspection.py` preflight — acceptance: SAFE on `ecus_source.pdf`, WARN with signature fields on `ecus_signed.pdf`, BLOCK on non-PDF/encrypted synthetic; unit tests green (covers: S2)
- [x] T3: Implement ByteRange extract + validate + content preservation hash — acceptance: valid ByteRange on `ecus_signed.pdf`; detects truncated/tampered range in unit test (covers: S2)
- [x] T4: Implement structural baseline report source vs ECUS-signed — acceptance: report includes page count, AcroForm, SigFlags, SubFilter, CMS subject/issuer/fingerprint; integration test asserts known values from spec §2 (covers: S1; S2)
- [x] T5: Generate ephemeral test certificate helper — acceptance: RSA cert usable by pyHanko; no private key written under repo paths in test run (covers: S2)
- [x] T6: Implement `PdfSigningEngine` sign+verify with test cert on `ecus_source.pdf` copy — acceptance: output verifies cryptographically; ByteRange valid; source hash unchanged; no SUCCESS if verify fails (covers: S1; S2; depends: T1, T5)
- [x] T7: Golden regression suite — acceptance: `uv run pytest` all green including new integration tests; record evidence in `.ai/` (covers: S1; depends: T2–T6)
- [x] T8: Independent review (PDF/PKI + security lens) — acceptance: `.ai/reviews/phase1-pdf-pki.md` + security notes; critical findings fixed or documented (covers: S2; depends: T7)
- [x] T9: Control-plane + commit hygiene — acceptance: PROJECT_STATE / NEXT_ACTION / SESSION_HANDOFF updated; commits on main with tests passing (covers: S2; depends: T7, T8)

## Acceptance criteria (phase)

1. `uv run pytest` exits 0 with new Phase 1 tests included.
2. Preflight classifies both golden fixtures as designed.
3. Test-cert signed PDF opens and cryptographically verifies.
4. `ecus_source.pdf` and `ecus_signed.pdf` SHA-256 unchanged (match START_HERE).
5. No private key, PIN, or raw CMS logged or committed.
6. No claim of PUS acceptance in code, docs, or status labels.
7. Review artifact exists before Finalize.
