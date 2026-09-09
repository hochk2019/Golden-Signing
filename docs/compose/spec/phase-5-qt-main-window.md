---
feature: phase-5-qt-main-window
status: delivered
updated: 2026-09-09
branch: main
commits: e569e64..HEAD # Phase 5 Qt main window
---

# Phase 5 — Qt Main Window (0.1.0-alpha)

## Report

**What was built** — Installed PySide6 6.11.2 (`uv sync --extra ui`). Implemented light-theme QSS from design tokens, `FileJobTableModel`, and `MainWindow`: brand rail (mark + Golden Signing), drop zone, add PDF/folder, job table, summary, **KÝ SỐ** CTA running `BatchEngine` + lab `TestCertPdfSigner` + PUS Safe profile into `signed/` beside the first input. Bootstrap launches the app. Offscreen unit tests construct window, add files, enable CTA.

**Verification** — full `pytest -q` exit 0 with `QT_QPA_PLATFORM=offscreen`; 5 UI tests; mypy/ruff ui clean.

**Journey log**
1. User approved `golden-mark` → Qt gate opened.
2. Icon-only crop of VTracer logo was incomplete; full diamond badge shipped earlier.
3. Keep UI copy as “Lab certificate” until USB token path is real.
4. Manual on-screen check still recommended (offscreen ≠ pixel QA).

## [S1] Problem

Design gate is approved (user OK on `golden-mark`). Core (sign, batch, PUS Safe, token shell) exists without UI. Spec §4/§5/§30 Phase 5 needs a first usable window: add PDFs, see readiness, run lab batch sign with progress, one primary CTA. No USB token this session — lab test certificate path only.

## [S2] Design

### Workspace

`main` (prior consent). Commit only, no push. User approved mark → proceed to Qt.

### Scope (minimal usable)

```
src/golden_signing/ui/
  theme.py         # QSS from DESIGN_TOKENS
  file_table.py    # QAbstractTableModel for jobs
  main_window.py   # sidebar + workspace + CTA
app/bootstrap.py   # QApplication entry (exists stub)
```

### Layout (UX_BRIEF)

- Left rail 220px: mark 36px + “Golden Signing” + “Ký số PDF”
- Workspace: drop zone, [Thêm PDF], [Thêm thư mục], table (name, pages, status, message), summary `n thành công / m lỗi`, profile label **PUS Safe (lab cert)**, primary **KÝ SỐ**
- Drag & drop PDF paths onto window
- Sign runs `BatchEngine` + `TestCertPdfSigner` + `pus_safe_profile` sequentially; progress callback updates rows
- Never overwrite sources; outputs to `<source_dir>/signed/` or user-chosen output folder (default `signed` subfolder next to first file)

### Theme

QSS: navy `#1E3A5F` primary button, gold accent sparingly, Segoe UI, light background `#F8FAFC`.

### Tests

Offscreen Qt (`QT_QPA_PLATFORM=offscreen`): construct window, add fake paths, model rows, theme applied, sign button enabled/disabled logic. Do not require display.

### Out of Scope

- Real token cert picker
- History / appearance designer / updater UI
- Dark mode toggle (tokens exist; UI light-only first)
- Installer

## Tasks

- [x] T1: theme.py QSS tokens (covers: S2)
- [x] T2: file table model + tests (covers: S2)
- [x] T3: main_window layout + drag-drop + add files (covers: S1; depends: T1–T2)
- [x] T4: wire KÝ SỐ → BatchEngine lab path + progress (covers: S1; depends: T3)
- [x] T5: bootstrap main() launches window (covers: S1; depends: T3)
- [x] T6: offscreen UI tests + full pytest + review + commit (covers: S2; depends: T1–T5)

## Acceptance

1. `pytest` exit 0 including offscreen UI tests.
2. Window constructs offscreen; table lists added PDFs.
3. KÝ SỐ signs lab batch; sources unchanged; outputs under signed/.
4. Theme applies navy primary CTA.
5. No PUS/token claims in UI copy.
