# NEXT ACTION

**Single recommended next step after this session:**

Phase 1 PDF laboratory is delivered on `main`. Next is **Phase 2 — Token abstraction** (spec §30):

1. PKCS#11 library discovery
2. Enumerate slots / certificates / private keys
3. Login session + PIN prompt only when necessary
4. Sign digest sequentially (never parallelize crypto on one token)
5. Reconnect / timeout / unplug handling (`SIGNING → TOKEN_LOST → WAITING_TOKEN`)

Do **not** start PySide6 UI until UI/UX Pro Max brief + design tokens exist (spec §46.1).
Do **not** claim PUS compatibility without real PUS upload test.

## Known Phase 1 limitations (accepted)

- Encrypted-PDF preflight unit case may classify as unreadable BLOCK rather than true `/Encrypt` detection.
- `TestCertPdfSigner` signatures not yet identical to `PdfSigningEngine` Protocol (lab adapter).
- Self-signed test cert produces certvalidator path-building warnings (expected; integrity still verified).

## Do not

- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs; use atomic output only.
