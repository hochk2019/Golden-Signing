# WORK LOG

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
