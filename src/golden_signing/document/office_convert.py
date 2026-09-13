"""MS Word/Excel COM → PDF (v1.1). Serialize COM; never mutate source."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from golden_signing.document.types import DocumentType

__all__ = [
    "ConversionError",
    "ConversionResult",
    "convert_office_to_pdf",
    "ms_office_available",
]

_COM_LOCK = threading.Lock()
_TIMEOUT_S = 120


class ConversionError(RuntimeError):
    """Office conversion failed with a stable error code."""

    def __init__(self, message: str, *, code: str = "CONVERSION_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ConversionResult:
    source: Path
    output_pdf: Path
    provider: str
    page_count: int | None = None


def ms_office_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    for cls in ("Word.Application", "Excel.Application"):
        try:
            import win32com.client as win32

            app = win32.Dispatch(cls)
            app.Quit()
            del app
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _validate_pdf(pdf: Path) -> int:
    if not pdf.is_file() or pdf.stat().st_size <= 0:
        raise ConversionError("PDF đầu ra không hợp lệ", code="CONVERSION_FAILED")
    try:
        import pikepdf

        with pikepdf.open(pdf) as doc:
            n = len(doc.pages)
        if n < 1:
            raise ConversionError("PDF đầu ra không có trang", code="CONVERSION_FAILED")
        return n
    except ConversionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(f"Không mở được PDF đầu ra: {exc}") from exc


def _convert_word(source: Path, output: Path) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False)
        # 17 = wdExportFormatPDF
        doc.ExportAsFixedFormat(str(output), 17)
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(
            f"Không thể chuyển Word sang PDF: {exc}", code="OFFICE_COM_ERROR"
        ) from exc
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:  # noqa: BLE001
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:  # noqa: BLE001
            pass
        pythoncom.CoUninitialize()


def _convert_excel(source: Path, output: Path) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = None
    wb = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Open(str(source), ReadOnly=True)
        # 0 = xlTypePDF
        wb.ExportAsFixedFormat(0, str(output))
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(
            f"Không thể chuyển Excel sang PDF: {exc}", code="OFFICE_COM_ERROR"
        ) from exc
    finally:
        try:
            if wb is not None:
                wb.Close(False)
        except Exception:  # noqa: BLE001
            pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:  # noqa: BLE001
            pass
        pythoncom.CoUninitialize()


def _convert_libreoffice(source: Path, output: Path) -> None:
    import shutil
    import subprocess
    import tempfile

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ConversionError(
            "Không tìm thấy Microsoft Office hoặc LibreOffice", code="NO_CONVERTER"
        )
    with tempfile.TemporaryDirectory(prefix="gs-lo-") as td:
        cmd = [
            soffice,
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            td,
            str(source),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=_TIMEOUT_S, capture_output=True)
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                f"LibreOffice chuyển đổi thất bại: {exc}", code="OFFICE_LO_ERROR"
            ) from exc
        produced = Path(td) / f"{source.stem}.pdf"
        if not produced.is_file():
            raise ConversionError("LibreOffice không tạo PDF", code="OFFICE_LO_ERROR")
        output.write_bytes(produced.read_bytes())


def convert_office_to_pdf(
    source: Path,
    output_pdf: Path,
    *,
    doc_type: DocumentType | None = None,
) -> ConversionResult:
    """Convert DOC/DOCX/XLS/XLSX to PDF. Thread-safe via process-wide lock."""
    source = Path(source)
    output_pdf = Path(output_pdf)
    if not source.is_file():
        raise ConversionError(f"Không tìm thấy file: {source}", code="IO_ERROR")
    kind = doc_type or DocumentType.UNKNOWN
    if kind is DocumentType.UNKNOWN:
        from golden_signing.document.types import detect_document_type

        kind = detect_document_type(source)
    if kind not in (DocumentType.WORD, DocumentType.EXCEL):
        raise ConversionError("Không phải file Word/Excel", code="CONVERSION_FAILED")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with _COM_LOCK:
        provider = "ms-office"
        try:
            if kind is DocumentType.WORD:
                _convert_word(source, output_pdf)
            else:
                _convert_excel(source, output_pdf)
        except ConversionError as exc:
            if exc.code == "OFFICE_COM_ERROR":
                provider = "libreoffice"
                _convert_libreoffice(source, output_pdf)
            else:
                raise
        pages = _validate_pdf(output_pdf)
        return ConversionResult(
            source=source,
            output_pdf=output_pdf,
            provider=provider,
            page_count=pages,
        )
