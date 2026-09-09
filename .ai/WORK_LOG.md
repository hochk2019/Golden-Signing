# WORK LOG

## 2026-09-09 — Session 5 (Phase 4 batch engine, overnight autonomous)

- User: skip USB token; continue next phases overnight; decide blockers myself.
- Spec `docs/compose/spec/phase-4-batch-engine.md`.
- Implemented retry/worker/queue/recovery + 12 tests (isolation, pause, cancel, 10-file batch).
- Full pytest exit 0. Commit only, no push.
- Next is UI design gate (not Qt code yet).

## 2026-09-09 — Session 4 (Phase 3 PUS Safe profile)

- Spec `docs/compose/spec/phase-3-pus-safe-profile.md`.
- `signing/pus_safe.py` settings resolve + invariants; pdf_signer wired; golden `tests/regression/`.
- Full pytest exit 0; commit only, no push.
- Status: Phase 2+3 complete; real token + PUS upload pending.

## 2026-09-09 — Session 3 (Phase 2 token abstraction)

- User: commit, no push, continue next task carefully with compose-next.
- Spec `docs/compose/spec/phase-2-token-abstraction.md` written; implemented without extra Grill (requirements from §30 + TOKEN_COMPATIBILITY).
- Built token/base, discovery, session manager, Pkcs11Backend, FakeTokenBackend + 23 tests.
- Independent review subagent APIError → in-session review artifact `.ai/reviews/phase2-token.md`.
- Fixed assert → TokenError on non-logged-in sign.
- Evidence: full pytest exit 0; mypy/ruff token modules clean.
- Status: `PHASE 2 TOKEN ABSTRACTION COMPLETE (FAKE+PKCS11 SHELL) / REAL TOKEN + PUS VALIDATION PENDING`.

### Open issues

- Real USB token matrix still TBD.
- Token-backed PDF signing (wire SignerBackend into engine) is Phase 3+.
- CSP/KSP fallback not implemented.

## 2026-09-09 — Session 2 (Phase 1 PDF laboratory)

- compose-next Orient on existing Phase 0 repo; user approved Phase 1 on **main**.
- Spec feature doc `docs/compose/spec/phase-1-pdf-lab.md` written and approved before code.
- Implemented preflight, ByteRange integrity, ECUS baseline, ephemeral test cert, pyHanko sign+verify.
- Multi-agent lanes: T2/T3/T5 subagents produced code then APIError on wrap-up; orchestrator verified. Independent review subagent succeeded.
- ECUS baseline confirmed vs spec §2.2/§2.3 (Signature1, Adobe.PPKMS, adbe.pkcs7.sha1, ByteRange, ICH CUBE / CA2).
- Fixed review findings: verify hard-fail; temp+`os.replace` atomic promote.
- Evidence: pytest 70 pass; mypy/ruff Phase 1 clean; fixture hashes unchanged.

### Open issues

- Spec version banner 1.2.0 vs end-of-file 1.1.0 (N-001).
- Duplicate section number 44.5 (N-002).
- `golden.svg` 3.2MB — mark/PNG/ICO still needed before UI.
- Encrypted-PDF preflight realism (may BLOCK as unreadable).
- Protocol vs lab signer signature drift.
- PySide6 commercial license path until packaging.
- **PUS real-world validation still pending.**

## 2026-09-09 — Session 1 (Phase 0 bootstrap)

- Read full spec `Golden Signing v1.2.0.md` (3333 lines) + `golden.svg`.
- Verified toolchain: Python 3.13.1, uv, git 2.51; pypdfium2 4.30.1 and cryptography 43.0.3 present; pyHanko/PySide6 not yet installed.
- Confirmed pyHanko 0.37.0 on PyPI (MIT, extras pkcs11/etsi/image-support/qr).
- User decisions: Phase 0 only; REVISION_NOTE (no spec edit); token available later; user copied golden PDFs.
- Initialized git, scaffold dirs, moved fixtures, hashed PDFs (4 pages each).
- Created `.ai/` control-plane.

### Open issues

- Spec version banner 1.2.0 vs end-of-file 1.1.0.
- Duplicate section number 44.5.
- `golden.svg` is 3.2MB VTracer output — needs mark/PNG/ICO derivatives later (Phase 5/branding).
- PySide6 commercial license path unresolved until release packaging.
