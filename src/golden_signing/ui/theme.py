"""Qt stylesheet from docs/design/DESIGN_TOKENS.md (light theme first)."""

from __future__ import annotations

from pathlib import Path

__all__ = ["LIGHT_QSS", "apply_theme"]

PRIMARY = "#1E3A5F"
ON_PRIMARY = "#FFFFFF"
GOLD = "#FDBE00"
BACKGROUND = "#F8FAFC"
SURFACE = "#FFFFFF"
FOREGROUND = "#0F172A"
MUTED_FG = "#475569"
BORDER = "#CBD5E1"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DESTRUCTIVE = "#DC2626"

LIGHT_QSS = f"""
QWidget {{
    background: {BACKGROUND};
    color: {FOREGROUND};
    font-family: "Segoe UI", "Open Sans", sans-serif;
    font-size: 12px;
}}
QMainWindow, QWidget#sidebar {{
    background: {SURFACE};
}}
QLabel#productTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {PRIMARY};
}}
QLabel#productSub {{
    font-size: 11px;
    color: {MUTED_FG};
}}
QFrame#rail {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 28px;
}}
QPushButton:hover {{
    border-color: {PRIMARY};
}}
QPushButton#primaryCta {{
    background: {PRIMARY};
    color: {ON_PRIMARY};
    border: 1px solid {PRIMARY};
    font-weight: 600;
    min-height: 36px;
    font-size: 13px;
}}
QPushButton#primaryCta:hover {{
    background: #16304f;
}}
QPushButton#primaryCta:disabled {{
    background: #94A3B8;
    border-color: #94A3B8;
}}
QTableWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: #E9EEF5;
}}
QHeaderView::section {{
    background: #E9EEF5;
    color: {MUTED_FG};
    border: none;
    padding: 6px;
    font-weight: 600;
}}
QLabel#dropHint {{
    color: {MUTED_FG};
    border: 2px dashed {BORDER};
    border-radius: 8px;
    padding: 24px;
    background: {SURFACE};
}}
QLabel#statusOk {{ color: {SUCCESS}; font-weight: 600; }}
QLabel#statusWarn {{ color: {WARNING}; font-weight: 600; }}
QLabel#statusErr {{ color: {DESTRUCTIVE}; font-weight: 600; }}
QLabel#goldAccent {{ color: #A16207; }}
QCheckBox {{
    spacing: 8px;
    color: {FOREGROUND};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {PRIMARY};
    border-radius: 4px;
    background: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {GOLD};
    background: #FFF8E1;
}}
QCheckBox::indicator:checked {{
    background: {PRIMARY};
    border-color: {PRIMARY};
    image: url("{{check_url}}");
}}
QCheckBox::indicator:checked:disabled {{
    background: #94A3B8;
    border-color: #94A3B8;
}}
"""


def _check_icon_url() -> str:
    here = Path(__file__).resolve()
    root = here.parents[3]
    icon = root / "assets" / "ui" / "check.svg"
    if icon.is_file():
        return icon.as_uri().replace("\\", "/")
    return ""


LIGHT_QSS = LIGHT_QSS.replace("{check_url}", _check_icon_url())


def apply_theme(app: object) -> None:
    app.setStyleSheet(LIGHT_QSS)  # type: ignore[attr-defined]
