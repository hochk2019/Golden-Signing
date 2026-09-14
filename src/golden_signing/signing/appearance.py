"""Visible signature appearance — Vietnamese font, no heavy border, text color."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from pyhanko.pdf_utils.content import PdfContent
from pyhanko.pdf_utils.layout import BoxConstraints

from golden_signing.signing.contracts import SigningProfile
from golden_signing.ui.cert_label import (
    common_name_from_subject,
    mst_from_subject,
)

__all__ = [
    "DEFAULT_TEXT_COLORS",
    "DEFAULT_VISIBLE_BOX",
    "build_stamp_text",
    "estimate_stamp_box",
    "resolve_vietnamese_font",
    "signing_extras",
]

# Fallback box if estimation is skipped (content-tight defaults used when signing).
DEFAULT_VISIBLE_BOX: tuple[int, int, int, int] = (40, 40, 300, 130)

# Very light panel so document content remains readable underneath.
PANEL_RGB: tuple[float, float, float] = (0.973, 0.980, 0.988)  # ~#F8FAFC
PANEL_OPACITY = 0.55
BORDER_RGB: tuple[float, float, float] = (0.86, 0.88, 0.90)

FONT_SIZE = 10
LEADING = 13
_PAD_X = 8
_PAD_Y = 6
PANEL_OPACITY_DEFAULT = 0.55

# Preset text colors (RGB 0-1 for pyHanko)
DEFAULT_TEXT_COLORS: dict[str, tuple[float, float, float]] = {
    "navy": (0.118, 0.227, 0.373),  # #1E3A5F
    "black": (0.05, 0.05, 0.05),
    "dark_blue": (0.075, 0.208, 0.42),
    "forest": (0.086, 0.42, 0.29),  # professional green
    "burgundy": (0.42, 0.09, 0.12),
    "gray": (0.29, 0.33, 0.41),
}

_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
)


def resolve_vietnamese_font() -> str | None:
    """First Windows TTF that supports Vietnamese diacritics."""
    for p in _FONT_CANDIDATES:
        path = Path(p)
        if path.is_file():
            return str(path)
    return None


def fold_vietnamese(text: str) -> str:
    """ASCII-safe Vietnamese for PDF stamps.

    pyHanko's OpenType embed path mis-renders VN diacritics in some viewers
    (Foxit/PDFium). Folding keeps company names readable on every viewer.
    """
    table = {
        "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
        "đ": "d",
    }
    out: list[str] = []
    for ch in text:
        if ch in table:
            out.append(table[ch])
            continue
        low = ch.lower()
        if low in table:
            mapped = table[low]
            out.append(mapped.upper() if ch.isupper() else mapped)
            continue
        out.append(ch)
    return "".join(out)


def build_stamp_text(
    *,
    company: str | None = None,
    mst: str | None = None,
    serial: str | None = None,
    expires: str | None = None,
    signer_display: str | None = None,
    when: str | None = None,
) -> str:
    return fold_vietnamese(
        _build_raw_stamp_text(
            company=company,
            mst=mst,
            serial=serial,
            expires=expires,
            signer_display=signer_display,
            when=when,
        )
    )


def _build_raw_stamp_text(
    *,
    company: str | None = None,
    mst: str | None = None,
    serial: str | None = None,
    expires: str | None = None,
    signer_display: str | None = None,
    when: str | None = None,
) -> str:
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


LOGO_SIZE = 36
DEFAULT_LOGO_NAME = "golden-mark.png"


def default_logo_path() -> Path | None:
    root = Path(__file__).resolve().parents[3]
    p = root / "assets" / "branding" / DEFAULT_LOGO_NAME
    return p if p.is_file() else None


class _StampCard(PdfContent):
    """Panel + optional logo mark on the left of the signature block."""

    def __init__(
        self,
        width: float,
        height: float,
        rgb: tuple[float, float, float],
        *,
        logo_path: Path | None = None,
        logo_size: float = LOGO_SIZE,
        show_panel: bool = True,
    ) -> None:
        super().__init__(box=BoxConstraints(width=width, height=height))
        self._rgb = rgb
        self._logo_path = logo_path
        self._logo_size = logo_size
        self._show_panel = show_panel
        self._logo: Any = None

    def set_writer(self, writer: Any) -> None:
        self.writer = writer
        if self._logo_path and self._logo_path.is_file() and writer is not None:
            from pyhanko.pdf_utils.images import PdfImage

            try:
                self._logo = PdfImage(
                    str(self._logo_path),
                    writer=writer,
                    box=BoxConstraints(width=self._logo_size, height=self._logo_size),
                )
            except Exception:  # noqa: BLE001
                self._logo = None

    def render(self) -> bytes:
        w = float(self.box.width or 0)
        h = float(self.box.height or 0)
        parts: list[bytes] = []
        if self._show_panel:
            r, g, b = self._rgb
            br, bg, bb = BORDER_RGB
            parts.append(
                (
                    f"{r:.3f} {g:.3f} {b:.3f} rg 0 0 {w:.2f} {h:.2f} re f "
                    f"{br:.3f} {bg:.3f} {bb:.3f} RG 0.5 w 0.25 0.25 {w - 0.5:.2f} {h - 0.5:.2f} re S"
                ).encode("ascii")
            )
        if self._logo is not None:
            # Vertically center logo on the left gutter
            ly = max(0.0, (h - self._logo_size) / 2.0)
            try:
                logo_ops = self._logo.render()
                # Critical: pull XObject / resources into this appearance stream
                with contextlib.suppress(Exception):
                    self.import_resources(self._logo.resources)
            except Exception:  # noqa: BLE001
                logo_ops = b""
            if logo_ops:
                parts.append(f"q 1 0 0 1 6 {ly:.2f} cm".encode("ascii"))
                parts.append(logo_ops)
                parts.append(b"Q")
        return b" ".join(parts) if parts else b""


def estimate_stamp_box(
    stamp_text: str,
    *,
    origin: tuple[int, int] = (40, 40),
    with_logo: bool = False,
) -> tuple[int, int, int, int]:
    """Tight box hugging stamp text; reserve left gutter when logo is on."""
    lines = stamp_text.split("\n") or [""]
    max_chars = max((len(line) for line in lines), default=1)
    text_w = int(max_chars * FONT_SIZE * 0.52)
    logo_w = (LOGO_SIZE + 12) if with_logo else 0
    width = text_w + logo_w + _PAD_X * 2
    height = max(len(lines) * LEADING + _PAD_Y * 2 + 2, LOGO_SIZE + 12 if with_logo else 0)
    x0, y0 = origin
    return (x0, y0, x0 + max(width, 160), y0 + max(height, 48))


def _make_text_style(
    *,
    font_size: int = FONT_SIZE,
    leading: int = LEADING,
    text_color: tuple[float, float, float] | None = None,
    prefer_embedded_vn: bool = True,
) -> Any:
    from pyhanko.pdf_utils.text import TextBoxStyle

    text_col = text_color or DEFAULT_TEXT_COLORS["navy"]
    if prefer_embedded_vn:
        font_path = resolve_vietnamese_font()
        if font_path:
            try:
                from pyhanko.pdf_utils.font.opentype import GlyphAccumulatorFactory

                return TextBoxStyle(
                    font=GlyphAccumulatorFactory(font_path, font_size=font_size),
                    font_size=font_size,
                    leading=leading,
                    border_width=0,
                    text_color=text_col,
                )
            except Exception:  # noqa: BLE001
                pass
    from pyhanko.pdf_utils.font.basic import SimpleFontEngineFactory

    return TextBoxStyle(
        font=SimpleFontEngineFactory("Helvetica", 0.5),
        font_size=font_size,
        leading=leading,
        border_width=0,
        text_color=text_col,
    )


def signing_extras(
    profile: SigningProfile | None,
    *,
    visible: bool,
    signer_display: str | None = None,
    cert_info: Any | None = None,
    text_color: tuple[float, float, float] | None = None,
    show_background: bool = True,
    background_opacity: float = PANEL_OPACITY_DEFAULT,
    show_logo: bool = False,
    logo_path: Path | str | None = None,
    origin: tuple[int, int] | None = None,
    page: int = 0,
) -> dict[str, Any]:
    """Visible stamp: tight box, optional soft background + logo, text color."""
    if not visible:
        return {}

    from pyhanko.pdf_utils.layout import AxisAlignment, Margins, SimpleBoxLayoutRule
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

    # Prefer full Vietnamese via embedded font; fold only if no font
    if resolve_vietnamese_font():
        stamp_text = _build_raw_stamp_text(
            company=company or signer_display,
            mst=mst,
            serial=serial,
            expires=expires,
            signer_display=signer_display,
        )
    else:
        stamp_text = build_stamp_text(
            company=company or signer_display,
            mst=mst,
            serial=serial,
            expires=expires,
            signer_display=signer_display,
        )

    field_name = "GoldenSigningVisible"
    use_logo = bool(show_logo)
    resolved_logo: Path | None = None
    if use_logo:
        resolved_logo = Path(logo_path) if logo_path else default_logo_path()
        use_logo = resolved_logo is not None and resolved_logo.is_file()

    box = estimate_stamp_box(stamp_text, with_logo=use_logo, origin=origin or (40, 40))
    card = _StampCard(
        width=float(box[2] - box[0]),
        height=float(box[3] - box[1]),
        rgb=PANEL_RGB,
        logo_path=resolved_logo if use_logo else None,
        show_panel=show_background,
    )
    text_left = _PAD_X + (LOGO_SIZE + 10 if use_logo else 0)
    opacity = min(1.0, max(0.05, float(background_opacity)))
    stamp = TextStampStyle(
        stamp_text=stamp_text,
        border_width=0,
        border_color=None,
        background=card if (show_background or use_logo) else None,
        background_layout=SimpleBoxLayoutRule(
            x_align=AxisAlignment.ALIGN_MIN,
            y_align=AxisAlignment.ALIGN_MIN,
            margins=Margins.uniform(0),  # type: ignore[no-untyped-call]
        ),
        background_opacity=opacity if show_background else 1.0,
        text_box_style=_make_text_style(text_color=text_color),
        inner_content_layout=SimpleBoxLayoutRule(
            x_align=AxisAlignment.ALIGN_MIN,
            y_align=AxisAlignment.ALIGN_MIN,
            margins=Margins(left=text_left, right=_PAD_X, top=_PAD_Y, bottom=_PAD_Y),
        ),
    )
    field_spec = SigFieldSpec(
        sig_field_name=field_name,
        on_page=max(0, int(page)),
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
