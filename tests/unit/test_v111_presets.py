"""v1.1.1: distinct compression presets + stamp opacity / VN font."""

from __future__ import annotations

from golden_signing.compress.engine import CompressionTier, default_profile
from golden_signing.signing.appearance import (
    _build_raw_stamp_text,
    fold_vietnamese,
    resolve_vietnamese_font,
)


def test_presets_are_distinct() -> None:
    loss = default_profile(CompressionTier.LOSSLESS)
    bal = default_profile(CompressionTier.BALANCED)
    pus = default_profile(CompressionTier.PUS_SAFE)
    assert loss.downsample is False
    assert bal.jpeg_quality > pus.jpeg_quality
    assert bal.max_dpi > pus.max_dpi
    assert pus.target_bytes == 400 * 1024
    assert loss.target_bytes is None
    assert bal.target_bytes is None
    assert loss.name != bal.name != pus.name


def test_pus_is_more_aggressive_than_balanced() -> None:
    pus = default_profile(CompressionTier.PUS_SAFE)
    bal = default_profile(CompressionTier.BALANCED)
    assert pus.jpeg_quality <= bal.jpeg_quality
    assert pus.max_dpi <= bal.max_dpi


def test_raw_stamp_keeps_diacritics() -> None:
    raw = _build_raw_stamp_text(company="CÔNG TY TNHH TEST")
    assert "CÔNG" in raw
    assert fold_vietnamese(raw).startswith("Da ky")


def test_resolve_font_on_windows() -> None:
    # On this build machine Segoe UI exists; if missing, None is OK
    p = resolve_vietnamese_font()
    assert p is None or str(p).lower().endswith((".ttf", ".otf"))
