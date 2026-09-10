"""Verify signatures in any PDF (no signing)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.signing.verify_pdf import verify_signed_pdf

__all__ = ["verify_pdf_file", "format_verify_report"]


def verify_pdf_file(path: Path):
    return verify_signed_pdf(path)


def format_verify_report(path: Path) -> str:
    r = verify_signed_pdf(path)
    lines = [
        f"File: {path.name}",
        f"Path: {path}",
        f"Hợp lệ mật mã: {'Có' if r.cryptographically_valid else 'Không'}",
        f"Đọc được chứng thư: {'Có' if r.certificate_readable else 'Không'}",
        f"Tài liệu bị sửa sau ký: {'Có' if r.document_modified else 'Không'}",
    ]
    if r.error_code:
        lines.append(f"Mã lỗi: {r.error_code}")
    if r.details:
        lines.append("Chi tiết:")
        lines.extend(f"  • {d}" for d in r.details)
    return "\n".join(lines)
