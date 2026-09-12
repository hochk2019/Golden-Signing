"""Qt stylesheet from docs/design/DESIGN_TOKENS.md (light theme first)."""

from __future__ import annotations

from pathlib import Path

__all__ = ["LIGHT_QSS", "apply_theme", "apply_window_icon"]

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
/* Labels must not paint the global #F8FAFC — breaks white sidebar/rail. */
QLabel {{
    background: transparent;
}}
QLabel#productTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {PRIMARY};
    background: transparent;
}}
QLabel#productSub {{
    font-size: 11px;
    color: {MUTED_FG};
    background: transparent;
}}
QLabel#productMeta {{
    font-size: 10px;
    color: {MUTED_FG};
    background: transparent;
}}
QLabel#brandMark {{
    background: transparent;
    padding: 0;
    margin: 0;
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
/* Compact row actions — must fit 36px table row with full bottom border. */
QPushButton#tableActionBtn {{
    padding: 0 8px;
    min-height: 22px;
    max-height: 22px;
    border-radius: 4px;
    font-size: 11px;
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
    selection-background-color: #D6E4F5;
    selection-color: {FOREGROUND};
}}
QTableWidget::item:selected {{
    background: #D6E4F5;
    color: {FOREGROUND};
}}
QTableWidget::item:selected:active {{
    background: #C5D8F0;
    color: {FOREGROUND};
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
    width: 12px;
    height: 12px;
    border: 1.5px solid {PRIMARY};
    border-radius: 3px;
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
/* Token dialogs */
QFrame#dlgHeader {{
    background: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QFrame#dlgFooter {{
    background: {SURFACE};
    border: none;
    border-top: 1px solid {BORDER};
}}
QWidget#dlgBody {{
    background: {BACKGROUND};
}}
QLabel#dlgTitle {{
    font-size: 16px;
    font-weight: 600;
    color: {PRIMARY};
    background: transparent;
}}
QLabel#dlgSubtitle {{
    font-size: 12px;
    color: {MUTED_FG};
    background: transparent;
}}
QLabel#fieldLabel {{
    font-size: 12px;
    font-weight: 600;
    color: {FOREGROUND};
    background: transparent;
}}
QFrame#certCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    border-left: 3px solid {BORDER};
}}
QFrame#certCard[selected="true"] {{
    background: #E8F0FB;
    border-color: {PRIMARY};
    border-left: 3px solid {PRIMARY};
}}
QLabel#certCardTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {FOREGROUND};
    background: transparent;
}}
QLabel#certCardMeta {{
    font-size: 11px;
    color: {MUTED_FG};
    background: transparent;
}}
QLineEdit#pinInput {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    background: {SURFACE};
    font-size: 13px;
}}
QLineEdit#pinInput:focus {{
    border: 1.5px solid {PRIMARY};
}}
QPushButton#btnSecondary {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
    color: {FOREGROUND};
}}
QPushButton#btnSecondary:hover {{
    border-color: {PRIMARY};
}}
"""


def _check_icon_url() -> str:
    here = Path(__file__).resolve()
    root = here.parents[3]
    icon = root / "assets" / "ui" / "check.svg"
    if icon.is_file():
        # Qt QSS prefers plain path with forward slashes (no file://)
        return icon.as_posix()
    return ""


LIGHT_QSS = LIGHT_QSS.replace("{check_url}", _check_icon_url())


def apply_theme(app: object) -> None:
    from PySide6.QtGui import QIcon

    from golden_signing.storage.app_paths import app_icon_path

    app.setStyleSheet(LIGHT_QSS)  # type: ignore[attr-defined]
    icon = app_icon_path()
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))  # type: ignore[attr-defined]


def apply_window_icon(widget: object) -> None:
    """Set brand icon on a top-level window/dialog (Windows title bar)."""
    from PySide6.QtGui import QIcon

    from golden_signing.storage.app_paths import app_icon_path

    icon = app_icon_path()
    if icon.is_file():
        widget.setWindowIcon(QIcon(str(icon)))  # type: ignore[attr-defined]
