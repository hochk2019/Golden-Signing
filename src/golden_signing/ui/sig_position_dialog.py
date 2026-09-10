"""Click-to-place signature position on a PDF page preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

__all__ = ["SigPositionDialog"]


class _PreviewLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(480, 360)
        self._img: QImage | None = None
        self._pdf_w = 1.0
        self._pdf_h = 1.0
        self._click_pdf: tuple[int, int] | None = None
        self._mark = None

    def set_page(self, img: QImage, pdf_w: float, pdf_h: float) -> None:
        self._img = img
        self._pdf_w = max(pdf_w, 1.0)
        self._pdf_h = max(pdf_h, 1.0)
        self._click_pdf = None
        self._repaint()

    def mousePressEvent(self, ev) -> None:  # noqa: ANN001, N802
        if self._img is None:
            return
        # Map widget click → image coords → PDF coords (origin bottom-left)
        iw, ih = self._img.width(), self._img.height()
        ww, wh = self.width(), self.height()
        # letterboxed
        scale = min(ww / iw, wh / ih)
        dw, dh = iw * scale, ih * scale
        ox = (ww - dw) / 2
        oy = (wh - dh) / 2
        x = (ev.position().x() - ox) / scale
        y = (ev.position().y() - oy) / scale
        if x < 0 or y < 0 or x > iw or y > ih:
            return
        pdf_x = int(round(x / iw * self._pdf_w))
        pdf_y = int(round((1.0 - y / ih) * self._pdf_h))
        self._click_pdf = (pdf_x, pdf_y)
        self._repaint()

    @property
    def selected_pdf_xy(self) -> tuple[int, int] | None:
        return self._click_pdf

    def _repaint(self) -> None:
        if self._img is None:
            return
        pix = self._img.copy()
        if self._click_pdf:
            iw, ih = pix.width(), pix.height()
            px = int(self._click_pdf[0] / self._pdf_w * iw)
            py = int((1.0 - self._click_pdf[1] / self._pdf_h) * ih)
            painter = QPainter(pix)
            pen = QPen(QColor(30, 58, 95))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawEllipse(px - 14, py - 14, 28, 28)
            painter.drawLine(px - 20, py, px + 20, py)
            painter.drawLine(px, py - 20, px, py + 20)
            painter.end()
        self.setPixmap(
            QPixmap.fromImage(pix).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class SigPositionDialog(QDialog):
    """Pick signature box origin (PDF bottom-left) by clicking a page preview."""

    def __init__(
        self,
        pdf_path: Path,
        *,
        page: int = 0,
        origin: tuple[int, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chọn vị trí chữ ký")
        self.setMinimumSize(640, 560)
        self.setModal(True)
        self._pdf_path = Path(pdf_path)
        self._result: tuple[int, int, int] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(QLabel("Bấm vào trang PDF để đặt góc dưới-trái của ô chữ ký:"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Trang:"))
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(0)
        self._page_spin.setMaximum(0)
        row.addWidget(self._page_spin)
        self._reset_btn = QPushButton("Về mặc định")
        self._reset_btn.clicked.connect(self._reset_default)
        row.addWidget(self._reset_btn)
        row.addStretch(1)
        self._pos_label = QLabel("Chưa chọn")
        row.addWidget(self._pos_label)
        root.addLayout(row)

        self._preview = _PreviewLabel()
        root.addWidget(self._preview, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Dùng vị trí này")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._origin = origin
        self._load_pages()
        self._page_spin.valueChanged.connect(lambda _v: self._render())
        if origin:
            self._preview._click_pdf = origin  # noqa: SLF001
        self._render()

    def _load_pages(self) -> None:
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(self._pdf_path))
            n = len(doc)
            doc.close()
            self._page_spin.setMaximum(max(0, n - 1))
        except Exception:  # noqa: BLE001
            self._page_spin.setMaximum(0)

    def _render(self) -> None:
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(self._pdf_path))
            page = doc[self._page_spin.value()]
            w, h = page.get_size()
            bitmap = page.render(scale=1.5)
            img = bitmap.to_pil()
            from PySide6.QtGui import QImage

            rgb = img.convert("RGBA")
            data = rgb.tobytes("raw", "RGBA")
            qimg = QImage(data, rgb.width, rgb.height, QImage.Format.Format_RGBA8888).copy()
            self._preview.set_page(qimg, float(w), float(h))
            if self._preview.selected_pdf_xy:
                x, y = self._preview.selected_pdf_xy
                self._pos_label.setText(f"({x}, {y}) trang {self._page_spin.value() + 1}")
            doc.close()
        except Exception as exc:  # noqa: BLE001
            self._pos_label.setText(f"Lỗi preview: {exc}")

    def _reset_default(self) -> None:
        self._preview._click_pdf = None  # noqa: SLF001
        self._origin = None
        self._pos_label.setText("Mặc định (40, 40)")
        self._render()

    def _accept(self) -> None:
        xy = self._preview.selected_pdf_xy
        page = self._page_spin.value()
        if xy:
            self._result = (page, xy[0], xy[1])
        else:
            self._result = (page, 40, 40)
        self.accept()

    def result_position(self) -> tuple[int, int, int] | None:
        """(page, x, y) or None if cancelled."""
        return self._result
