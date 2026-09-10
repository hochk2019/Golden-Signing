"""Visible signature appearance helpers (spec §5.5, §44.1)."""

from __future__ import annotations

from typing import Any

from golden_signing.signing.contracts import SigningProfile
from golden_signing.ui.cert_label import (
    common_name_from_subject,
    mst_from_subject,
)

__all__ = ["DEFAULT_VISIBLE_BOX", "build_stamp_text", "signing_extras"]

# PDF user space, origin bottom-left. Wider/taller box for multi-line company stamp.
DEFAULT_VISIBLE_BOX: tuple[int, int, int, int] = (40, 40, 400, 170)


def build_stamp_text(
    *,
    company: str | None = None,
    mst: str | None = None,
    serial: str | None = None,
    expires: str | None = None,
    signer_display: str | None = None,
    when: str | None = None,
) -> str:
    """Multi-line visible stamp body (Acrobat-like VN company signature block)."""
    from datetime import datetime

    if not when:
        when = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []
    company = (company or signer_display or "").strip()
    if company:
        lines.append(f"Đã ký bởi: {company}")
    else:
        lines.append("Đã ký số")
    if mst:
        lines.append(f"MST: {mst}")
    if serial:
        ser = serial if len(serial) <= 28 else serial[:27] + "…"
        lines.append(f"Serial: {ser}")
    if expires:
        exp = str(expires)[:10]
        lines.append(f"Hiệu lực đến: {exp}")
    lines.append(f"Thời gian ký: {when}")
    return "\n".join(lines)


def signing_extras(
    profile: SigningProfile | None,
    *,
    visible: bool,
    signer_display: str | None = None,
    cert_info: Any | None = None,
) -> dict[str, Any]:
    """Return new_field_spec + stamp_style when visible."""
    if not visible:
        return {}

    from pyhanko.pdf_utils.layout import AxisAlignment, Margins, SimpleBoxLayoutRule
    from pyhanko.pdf_utils.text import TextBoxStyle
    from pyhanko.sign.fields import SigFieldSpec, VisibleSigSettings
    from pyhanko.stamp import TextStampStyle

    company = None
    mst = None
    serial = None
    expires = None
    if cert_info is not None:
        subject = str(getattr(cert_info, "subject", "") or "")
        company = common_name_from_subject(subject)
        mst = mst_from_subject(subject)
        serial = getattr(cert_info, "serial", None) or None
        expires = getattr(cert_info, "not_valid_after", None) or None

    stamp_text = build_stamp_text(
        company=company or signer_display,
        mst=mst,
        serial=serial,
        expires=expires,
        signer_display=signer_display,
    )

    field_name = "GoldenSigningVisible"
    box = DEFAULT_VISIBLE_BOX
    stamp = TextStampStyle(
        stamp_text=stamp_text,
        border_width=1,
        background_opacity=0.92,
        text_box_style=TextBoxStyle(font_size=8, leading=10),
        inner_content_layout=SimpleBoxLayoutRule(
            x_align=AxisAlignment.ALIGN_MIN,
            y_align=AxisAlignment.ALIGN_MIN,
            margins=Margins(left=6, right=6, top=6, bottom=6),
        ),
    )
    field_spec = SigFieldSpec(
        sig_field_name=field_name,
        on_page=0,
        box=box,
        visible_sig_settings=VisibleSigSettings(
            rotate_with_page=True,
            scale_with_page_zoom=True,
            print_signature=True,
        ),
    )
    return {
        "new_field_spec": field_spec,
        "stamp_style": stamp,
        "field_name": field_name,
    }
