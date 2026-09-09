# NEXT ACTION

**When user wakes:**

1. **Glance at branding:** `assets/branding/golden-mark.png` and `golden-app-icon.ico` — OK for sidebar/taskbar? If not, provide icon-only cutout (no wordmark).
2. **Then Qt UI coding session** (Phase 5 implementation): main window, drag/drop, file list, cert/profile, KÝ SỐ CTA, batch progress — using `docs/design/*` tokens. Still no UI code without confirming mark.
3. USB token when available → `docs/TOKEN_COMPATIBILITY.md`.
4. PUS upload before any compatibility claim.

## Do not

- Do not start heavy Qt polish before user OK on mark (design gate human checkpoint).
- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs.
