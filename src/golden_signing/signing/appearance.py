"""Visible signature appearance helpers (spec §5.5, §44.1)."""

from __future__ import annotations

from typing import Any

from golden_signing.signing.contracts import SigningProfile

__all__ = ["DEFAULT_VISIBLE_BOX", "signing_extras"]

# PDF user space, origin bottom-left. Width 250, height 70 pt — compact corner stamp.
DEFAULT_VISIBLE_BOX: tuple[int, int, int, int] = (50, 50, 300, 120)


def signing_extras(
    profile: SigningProfile | None,
    *,
    visible: bool,
    signer_display: str | None = None,
) -> dict[str, Any]:
    """Return kwargs for pyhanko sign_pdf: new_field_spec + stamp_style when visible."""
    if not visible:
        return {}
    from datetime import datetime

    from pyhanko.pdf_utils.layout import AxisAlignment, Margins, SimpleBoxLayoutRule
    from pyhanko.sign.fields import SigFieldSpec, VisibleSigSettings
    from pyhanko.stamp import TextStampStyle

    name = signer_display or "Người ký"
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    stamp_text = f"Đã ký bởi: {name}\n{when}"

    field_name = "GoldenSigningVisible"
    box = DEFAULT_VISIBLE_BOX
    stamp = TextStampStyle(
        stamp_text=stamp_text,
        border_width=1,
        background_opacity=0.85,
        inner_content_layout=SimpleBoxLayoutRule(
            x_align=AxisAlignment.ALIGN_MIN,
            y_align=AxisAlignment.ALIGN_MIN,
            margins=Margins(left=4, right=4, top=4, bottom=4),
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
