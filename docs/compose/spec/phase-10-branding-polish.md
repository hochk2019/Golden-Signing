---
feature: phase-10-branding-polish
status: delivered
updated: 2026-09-11
branch: main
commits: 4a39bb1..HEAD
---

# Phase 10 — Branding polish (Golden Sign)

## Report

**What was built** — Window icon (`golden-app-icon.ico`) on QApplication + every main dialog. `productTitle`/`productSub` forced `background: transparent` so “Ký số PDF” matches sidebar. User-facing name **Golden Sign** (package `golden_signing` unchanged). About: non-profit disclaimer + customs consulting contact line. App data migrates once from `%LOCALAPPDATA%\GoldenSigning` → `GoldenSign`.

**Verification** — full `pytest -q` exit 0; smoke: title `Golden Sign — Ký số PDF`, icons non-null offscreen.

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
