# Phase 5 Qt Main Window Review

Date: 2026-09-09
Reviewer: orchestrator (autonomous UI session)
Spec: `docs/compose/spec/phase-5-qt-main-window.md`
Status: **PASS**

## Verification

| Command | Result |
|---|---|
| `pytest -q` (QT_QPA_PLATFORM=offscreen) | PASS exit 0 |
| UI unit tests | 5 passed |
| `ruff` ui modules | PASS |
| `mypy` ui modules | PASS |
| `uv sync --extra ui` | PySide6 6.11.2 installed |

## Compliance

- Mark OK by user → Qt coding unblocked.
- Main window: rail + Golden Signing + workspace + file table + KÝ SỐ CTA.
- Add PDF / folder / drag-drop; lab PUS Safe sign via BatchEngine.
- Theme navy primary CTA from DESIGN_TOKENS.
- No PUS/token claim (“Lab certificate” label).
- Offscreen tests only — manual GUI check still recommended on wake.

## Notes

- Dual table state (QTableWidget + FileJobTableModel) is simple; model is source of jobs.
- Output dir: `signed/` next to first input file.
- History / cert picker / dark mode deferred.
