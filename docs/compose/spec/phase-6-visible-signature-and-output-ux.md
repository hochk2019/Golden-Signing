---
feature: phase-6-visible-signature-and-output-ux
status: delivered
updated: 2026-09-09
branch: main
commits: 11027d9..275ba0c # Phase 6
---

# Phase 6 — Visible Signature + Output UX

## Report

**What was built** — Visible signature via pyHanko `PdfSigner` + `SigFieldSpec` + `TextStampStyle` (box 50,50–300,120 page 0). UI combo **Vô hình / Hiển thị trên PDF**. Shared `pyhanko_sign.py` used by lab and token signers. Output folder picker (blank → `signed` beside first input), **Mở thư mục**, **Mở file đã chọn**, **Xóa khỏi danh sách**. Invisible path unchanged; verify + atomic promote still enforced.

**Verification** — full `pytest -q` exit 0; 6 new tests including lab visible sign produces `GoldenSigningVisible` and crypto-valid.

**Journey log**
1. `sign_pdf()` has no `stamp_style` — must use `PdfSigner(...).sign_pdf()`.
2. `SimpleBoxLayoutRule` uses `AxisAlignment.ALIGN_MIN` + `Margins`, not x/y pixels.
3. Token signer uses same helper so visible works with USB token.

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
