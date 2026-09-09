# NEXT ACTION

**Single recommended next step after this session:**

Phase 2 token abstraction is delivered on `main` (fake + PKCS#11 shell). Next options in order:

1. **User plugs real USB token** — fill `docs/TOKEN_COMPATIBILITY.md`, run discovery + list certs + sign digest (no PDF yet).
2. **Phase 3 — PUS Safe production profile** (spec §30): wire profile → engine, golden fixture regression, still no PUS claim without upload test.
3. Then Phase 4 batch engine.

Do **not** start PySide6 UI until UI/UX Pro Max brief + design tokens exist (spec §46.1).
Do **not** claim PUS compatibility without real PUS upload test.

## Known Phase 2 limitations

- `Pkcs11Backend` not tested on real hardware.
- Windows CSP/KSP fallback not implemented.
- PDF engine still uses lab `TestCertPdfSigner`, not token-backed `SignerBackend` yet.

## Do not

- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs; use atomic output only.
