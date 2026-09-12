"""Offscreen UI tests (Phase 5)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.ui.file_table import FileJobTableModel  # noqa: E402
from golden_signing.ui.main_window import MainWindow  # noqa: E402
from golden_signing.ui.theme import LIGHT_QSS, apply_theme  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    return app


def test_theme_contains_primary(qapp: QApplication) -> None:
    assert "#1E3A5F" in LIGHT_QSS
    assert "primaryCta" in LIGHT_QSS
    assert qapp.styleSheet() != ""


def test_main_window_constructs(qapp: QApplication) -> None:
    win = MainWindow()
    assert win.windowTitle() == "Golden Sign — Sản phẩm của Golden Logistics"
    assert win._sign_btn.isEnabled() is False
    from PySide6.QtWidgets import QLabel

    texts = [b.text() for b in win.findChildren(QLabel)]
    assert "Designer: Hoc HK" in texts
    assert "Ký số PDF" in texts
    win.close()


def test_add_pdf_enables_sign(qapp: QApplication, tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(SOURCE_PDF.read_bytes())
    win = MainWindow()
    win.add_paths([pdf])
    assert win._model.rowCount() == 1
    assert win._sign_btn.isEnabled() is True
    assert win._table.rowCount() == 1
    win.close()


def test_add_folder_scans_pdfs(qapp: QApplication, tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_bytes(SOURCE_PDF.read_bytes())
    (tmp_path / "b.pdf").write_bytes(SOURCE_PDF.read_bytes())
    (tmp_path / "c.txt").write_text("x")
    win = MainWindow()
    win.add_paths([tmp_path])
    assert win._model.rowCount() == 2
    win.close()


def test_file_model_skips_duplicates(qapp: QApplication) -> None:
    model = FileJobTableModel()
    model.add_paths([SOURCE_PDF, SOURCE_PDF])
    assert model.rowCount() == 1


def test_action_buttons_equal_width(qapp: QApplication, tmp_path: Path) -> None:
    from PySide6.QtWidgets import QPushButton

    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(SOURCE_PDF.read_bytes())
    win = MainWindow()
    win.add_paths([pdf])
    wrap = win._table.cellWidget(0, 2)
    assert wrap is not None
    buttons = wrap.findChildren(QPushButton)
    assert len(buttons) == 3
    sizes = {(b.width(), b.height()) for b in buttons}
    assert sizes == {(88, 24)}
    win.close()


def test_blank_preview_has_page_border(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    from golden_signing.ui.sig_position_dialog import _PreviewLabel

    preview = _PreviewLabel()
    assert "background-color" in preview.styleSheet()
    img = QImage(100, 140, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)
    preview.resize(400, 400)
    preview.set_page(img, 100.0, 140.0, origin=None, box_w=40, box_h=20)
    pix = preview.pixmap()
    assert pix is not None and not pix.isNull()
    # Keep-aspect scale for 100x140 into 400x400 → page ~286x400, centered.
    # Interior of the blank page must stay white (border is edge-only).
    out = pix.toImage()
    cx, cy = out.width() // 2, out.height() // 2
    interior = out.pixelColor(cx, cy)
    assert interior.red() > 240 and interior.green() > 240 and interior.blue() > 240
