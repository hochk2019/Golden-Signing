---
feature: phase-10-branding-polish
status: delivered
updated: 2026-09-11
branch: main
commits: 4a39bb1..HEAD
---

# Phase 10 — Branding polish (Golden Sign)

## Report

**What was built** — Window icon (`golden-app-icon.ico`) on QApplication + every main dialog. All `QLabel`s `background: transparent` (global `QWidget` #F8FAFC no longer tints the white rail). Sidebar uses `golden-mark-ui.png` (near-white cleared). User-facing name **Golden Sign**. Title bar: `Golden Sign — Sản phẩm của Golden Logistics`. Sidebar: Golden Sign / Ký số PDF / **Designer: Hoc HK**. About: non-profit disclaimer + customs line. App data migrates once from `%LOCALAPPDATA%\GoldenSigning` → `GoldenSign`.

**Verification** — full `pytest -q` exit 0; smoke: title + Designer label.

## [S1] Problem

Default Qt/Python title-bar icon; “Ký số PDF” background mismatch; product rename; About copy.

## [S2] Design

- `storage/app_paths.py`: `app_icon_path`, `data_dir` (+ copy legacy)
- `theme.apply_theme` / `apply_window_icon`
- Rename UI strings only; keep `golden_signing` import path and QSettings `HOCHK/GoldenSigning`

## Tasks

- [x] T1 icons — acceptance: main + dialogs have brand icon
- [x] T2 productSub transparent
- [x] T3 rename UI/docs → Golden Sign
- [x] T4 About copy
- [x] T5 AppData migrate + tests
