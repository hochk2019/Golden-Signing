---
feature: phase-6-visible-signature-and-output-ux
status: delivered
updated: 2026-09-10
branch: main
commits: 11027d9..275ba0c # original Phase 6; follow-ups see Amendment A1
---

# Phase 6 — Visible Signature + Output UX

## Report

**What was built** — Visible signature via pyHanko `PdfSigner` + `SigFieldSpec` + `TextStampStyle`. UI combo **Vô hình / Hiển thị trên PDF**. Shared `pyhanko_sign.py` for lab and token signers. Output folder picker, **Mở thư mục**, **Mở file đã chọn**, **Xóa khỏi danh sách**. Invisible path unchanged; verify + atomic promote enforced.

**Verification** — full `pytest -q` exit 0; visible lab sign produces `GoldenSigningVisible` and crypto-valid.

**Journey log**
1. `sign_pdf()` has no `stamp_style` — must use `PdfSigner(...).sign_pdf()`.
2. `SimpleBoxLayoutRule` uses `AxisAlignment` + `Margins`, not x/y pixels.
3. Token signer uses same helper so visible works with USB token.

## Amendment A1 — Stamp polish (2026-09-09/10 follow-up)

User-driven refinements after original delivery. Same feature document; new tasks only.

### A1 added

| Item | Behavior |
|---|---|
| Default mode | **Hiển thị trên PDF** |
| Stamp body | Company + MST + Serial + expiry + sign time (from cert) |
| VN text | ASCII-fold diacritics (pyHanko OpenType mis-renders VN in Foxit/PDFium) |
| Typography | Helvetica 9/12; navy default |
| Text color | UI combo + `QSettings.signatureTextColor` |
| Background | Soft light panel `#F8FAFC` @ 55%; hairline `#CBD5E1` |
| BG toggle | Checkbox **Nền nhạt** + `QSettings.signatureBg` |
| Box size | `estimate_stamp_box()` hugs text (was fixed 360×135) |
| Checkbox UI | Navy border, navy+white check, 12px indicator |

### A1 related (not stamp-only)

- Empty-password permission-encrypted PDFs: preflight/sign/verify (`pdf/crypto.py`)
- Compact cert dialog + CN labels; auto-scan token; PIN via `token.open(user_pin=)`
- Output UX unchanged from original T3–T4

### A1 tasks

- [x] A1.1 Default visible + rich stamp text
- [x] A1.2 Fold VN + Helvetica + color picker persist
- [x] A1.3 Soft panel + toggle + tight box
- [x] A1.4 Checkbox affordance + size
- [x] A1.5 Encrypted PDF + token UX fixes
- [x] A1.6 Logo/seal in stamp (next)
- [ ] A1.7 Optional: restore true VN diacritics via non-pyHanko appearance path

### A1.6 Logo in stamp (2026-09-10)

- Optional logo (`assets/branding/golden-mark.png`, 36pt) left of stamp text
- UI checkbox **Logo** + `QSettings.signatureLogo` (default on if asset exists)
- Box widens automatically when logo enabled; text margins shift right
- Panel + logo drawn in shared `_StampCard` background content

### A1 still out of scope

- Drag-to-place stamp on preview
- Full appearance designer / multi-page placement
- Watch folder / CLI

## [S1] Problem

Signed PDFs verify but show **no visual signature** (invisible PUS Safe default). Users also lack: choose output folder, open signed folder/file, clear file list. Spec §44.1/§5.5 require visible/invisible as user choice with appearance; §5.3 output rules; §5.2 open output folder.

## [S2] Design

### Visible signature

- UI combo: **Vô hình** (default, PUS Safe) | **Hiển thị trên PDF**
- When visible: pyHanko `SigFieldSpec` + `TextStampStyle` — text “Đã ký bởi: {subject short}\n{time}”, box on page 0 bottom-left (PDF units, origin BL): `(50, 50, 300, 120)`
- Still: never overwrite source; post-sign verify; incremental update
- Invisible path unchanged (no field widget / default pyHanko)

Shared helper `signing/appearance.py`:

```python
def signing_extras(profile, *, visible: bool) -> dict  # new_field_spec, stamp_style
```

Wire into `TokenPdfSigner.sign` and `TestCertPdfSigner.sign`.

### Output UX (main window)

- `QLineEdit` + [Chọn…] — output folder; default `signed` beside first input; persist last path in-memory (session)
- Buttons after table: **Mở thư mục**, **Mở file đã chọn**, **Xóa khỏi danh sách**
- Context: select row → open that signed file if exists; else open folder
- Clear removes selected or all non-busy rows

### Out of Scope

- Appearance designer / logo in stamp / QR
- Drag placement on preview
- Watch folder / CLI

## Tasks

- [x] T1: `appearance.py` + profile flag `visible_signature` (covers: S2)
- [x] T2: Wire lab + token signers for visible field (covers: S1; depends: T1)
- [x] T3: UI mode combo + output folder picker (covers: S2)
- [x] T4: UI open folder / open file / clear list (covers: S2; depends: T3)
- [x] T5: Tests + verify + commit (covers: S1–S2; depends: T1–T4)

## Acceptance

1. `pytest` exit 0.
2. Visible mode creates signature field on page 0; invisible has no visible widget required.
3. Output folder changeable; signed files land there.
4. Open folder/file buttons work (path exists).
5. Clear removes rows.
6. Source PDFs unchanged; verify still enforced.
