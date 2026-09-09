# NEXT ACTION

**Single recommended next step after this session:**

Complete Phase 0 commit, then start Phase 1 PDF laboratory:

1. Confirm `uv sync` works and `python -c "import golden_signing"` smoke passes.
2. Phase 1 task order (from spec §30 Phase 1):
   - Parse `ecus_source.pdf` / `ecus_signed.pdf`
   - Detect existing signatures
   - Structural baseline compare (page count, AcroForm, ByteRange, CMS parse)
   - Sign with **test certificate** first (not USB token)
   - Post-sign verify + ByteRange integrity
3. Do **not** start PySide6 UI until UI/UX Pro Max brief + design tokens exist (spec §46.1).

## Do not

- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs; use atomic output only.
