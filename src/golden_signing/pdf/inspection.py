"""PDF inspection / preflight (Phase 1).

Preflight contract (spec §9, phase-1-pdf-lab S2):
- SAFE  : readable, not encrypted, no existing signatures / AcroForm
- WARN  : readable but has existing signature field(s) and/or AcroForm
- BLOCK : not a PDF, unreadable, or encrypted

Uses pypdfium2 for open/page-count and pyHanko for structure metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from golden_signing.signing.contracts import PreflightLevel, PreflightResult

__all__ = ["preflight_pdf"]


class _HankoMeta(TypedDict):
    encrypted: bool
    pdf_version: str
    incremental_revisions: int
    existing_signatures: list[str]
    has_acroform: bool


def _classify(
    *,
    encrypted: bool,
    existing_signatures: list[str],
    has_acroform: bool,
) -> PreflightLevel:
    if encrypted:
        return PreflightLevel.BLOCK
    if existing_signatures or has_acroform:
        return PreflightLevel.WARN
    return PreflightLevel.SAFE


def _check_writable(path: Path) -> bool:
    """Best-effort write-permission check without modifying the file."""
    try:
        if not path.exists():
            return False
        # Open for append in binary; if this raises PermissionError/OSError → False.
        # Closing immediately leaves file unchanged.
        with open(path, "ab"):
            pass
        return True
    except OSError:
        return False


def _inspect_with_pyhanko(path: Path) -> _HankoMeta:
    """Return structure metadata via pyHanko. Raises on unreadable/non-PDF."""
    from pyhanko.pdf_utils.generic import NameObject
    from pyhanko.pdf_utils.reader import PdfFileReader

    with open(path, "rb") as fh:
        reader = PdfFileReader(fh)
        encrypted = bool(reader.encrypted)
        version = reader.input_version
        pdf_version = (
            f"{version[0]}.{version[1]}" if isinstance(version, tuple) else str(version)
        )
        revisions = int(reader.total_revisions)

        existing_signatures: list[str] = []
        has_acroform = False

        root = reader.root
        if "/AcroForm" in root:
            has_acroform = True
            acro = root["/AcroForm"]
            fields_ref = acro.get("/Fields")
            if fields_ref is not None:
                for field_ref in fields_ref:
                    field = (
                        field_ref.get_object()
                        if hasattr(field_ref, "get_object")
                        else field_ref
                    )
                    ft = field.get("/FT")
                    if ft == NameObject("/Sig"):
                        name = str(field.get("/T", ""))
                        if name:
                            existing_signatures.append(name)
                        else:
                            existing_signatures.append("<unnamed-sig>")

    return {
        "encrypted": encrypted,
        "pdf_version": pdf_version,
        "incremental_revisions": revisions,
        "existing_signatures": existing_signatures,
        "has_acroform": has_acroform,
    }


def _page_count_pypdfium2(path: Path) -> int:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def preflight_pdf(input_path: Path, *, writable_check: bool = True) -> PreflightResult:
    """Inspect a PDF and return a PreflightResult.

    Never raises for missing/unreadable/non-PDF input — those become BLOCK.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # --- existence / size ------------------------------------------------
    if not input_path.exists():
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=[f"file not found: {input_path.name}"],
            file_size_bytes=0,
            writable=False,
        )

    try:
        file_size = input_path.stat().st_size
    except OSError as exc:
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=[f"cannot stat file: {exc}"],
            file_size_bytes=0,
            writable=False,
        )

    if file_size == 0:
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=["file is empty"],
            file_size_bytes=0,
            writable=False,
        )

    # --- header sniff ----------------------------------------------------
    try:
        header = input_path.read_bytes()[:8]
    except OSError as exc:
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=[f"cannot read file: {exc}"],
            file_size_bytes=file_size,
            writable=False,
        )

    if not header.startswith(b"%PDF-"):
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=["not a PDF (missing %PDF- header)"],
            file_size_bytes=file_size,
            writable=False,
        )

    # --- writable check --------------------------------------------------
    writable = _check_writable(input_path) if writable_check else True

    # --- structural inspection via pyHanko -------------------------------
    try:
        meta = _inspect_with_pyhanko(input_path)
    except Exception as exc:  # noqa: BLE001 — any parse failure → BLOCK
        errors.append(f"PDF unreadable / malformed: {exc}")
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=errors,
            file_size_bytes=file_size,
            writable=writable,
        )

    encrypted = meta["encrypted"]
    existing_signatures = meta["existing_signatures"]
    has_acroform = meta["has_acroform"]
    pdf_version = meta["pdf_version"]
    revisions = meta["incremental_revisions"]

    # --- encrypted is always BLOCK ---------------------------------------
    if encrypted:
        errors.append("PDF is encrypted / password-protected")
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=True,
            errors=errors,
            pdf_version=pdf_version,
            file_size_bytes=file_size,
            writable=writable,
            has_acroform=has_acroform,
            incremental_revisions=revisions,
        )

    # --- page count via pypdfium2 ----------------------------------------
    try:
        page_count = _page_count_pypdfium2(input_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot determine page count: {exc}")
        return PreflightResult(
            level=PreflightLevel.BLOCK,
            page_count=0,
            encrypted=False,
            errors=errors,
            pdf_version=pdf_version,
            file_size_bytes=file_size,
            writable=writable,
            has_acroform=has_acroform,
            incremental_revisions=revisions,
        )

    # --- warnings ---------------------------------------------------------
    if existing_signatures:
        warnings.append(
            f"document already contains {len(existing_signatures)} signature field(s); "
            "signing will append a new incremental revision"
        )
    if has_acroform and not existing_signatures:
        warnings.append("document contains an AcroForm (no signature fields detected)")

    # --- classify ---------------------------------------------------------
    level = _classify(
        encrypted=encrypted,
        existing_signatures=existing_signatures,
        has_acroform=has_acroform,
    )

    return PreflightResult(
        level=level,
        page_count=page_count,
        encrypted=encrypted,
        existing_signatures=existing_signatures,
        warnings=warnings,
        errors=errors,
        pdf_version=pdf_version,
        file_size_bytes=file_size,
        writable=writable,
        has_acroform=has_acroform,
        incremental_revisions=revisions,
    )
