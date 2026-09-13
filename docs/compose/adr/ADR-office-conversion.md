# ADR — Office → PDF conversion (v1.1.0)

**Status:** Accepted · 2026-09-11  
**Spike evidence:** `.spike/v11/` on build machine (Windows 11, Office 16)

## Decision

1. **Primary:** Microsoft Word/Excel COM via `pywin32` (`DispatchEx`), `ExportAsFixedFormat` / `ExportAsFixedFormat(type=0)`.
2. **Fallback:** LibreOffice `soffice --headless --convert-to pdf` if installed and COM fails.
3. **If neither works:** job → `CONVERSION_FAILED` with clear Vietnamese message; do not accept Office files silently.

## Constraints

- No macros; `DisplayAlerts=0`; never save over source.
- One COM instance at a time (serialize conversion).
- Validate PDF after convert: exists, size>0, pikepdf/pypdfium2 open, page count≥1.
- Timeout ~120s per file; cleanup Word/Excel in `finally`.

## Spike results

| Source | PDF size | Notes |
|---|---|---|
| Word DOCX (text, ~2 pages) | ~45 KB | ExportAsFixedFormat 17 |
| Excel XLSX (11 rows) | ~48 KB | ExportAsFixedFormat 0 |

## Consequences

- Add `pywin32` dependency (Windows only).
- Conversion runs in worker; UI stays responsive.
- Do not parallelize multiple Excel/Word instances.
