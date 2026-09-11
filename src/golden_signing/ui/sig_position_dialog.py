"""Click-to-place signature box on a PDF page preview (auto-clamped)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

# Typical stamp size (pt) used for preview box; actual box may be a bit tighter.
DEFAULT_STAMP_W = 240
DEFAULT_STAMP_H = 80


class _PreviewLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(520, 400)
        self._img: QImage | None = None
        self._pdf_w = 1.0
        self._pdf_h = 1.0
        self._origin: tuple[int, int] | None = None
        self._box_w = DEFAULT_STAMP_W
        self._box_h = DEFAULT_STAMP_H

    def set_page(
        self,
        img: QImage,
        pdf_w: float,
        pdf_h: float,
        *,
        origin: tuple[int, int] | None,
        box_w: int,
        box_h: int,
    ) -> None:
        self._img = img
        self._pdf_w = max(pdf_w, 1.0)
        self._pdf_h = max(pdf_h, 1.0)
        self._box_w = max(int(box_w), 40)
        self._box_h = max(int(box_h), 24)
        self._origin = self._clamp(origin) if origin else None
        self._repaint()

    def _clamp(self, origin: tuple[int, int]) -> tuple[int, int]:
        x = max(0, min(int(origin[0]), int(self._pdf_w - self._box_w)))
        y = max(0, min(int(origin[1]), int(self._pdf_h - self._box_h)))
        return (x, y)

    def mousePressEvent(self, ev: Any) -> None:  # noqa: ANN401, N802
        if self._img is None:
            return
        iw, ih = self._img.width(), self._img.height()
        ww, wh = self.width(), self.height()
        scale = min(ww / iw, wh / ih)
        dw, dh = iw * scale, ih * scale
        ox = (ww - dw) / 2
        oy = (wh - dh) / 2
        x = (ev.position().x() - ox) / scale
        y = (ev.position().y() - oy) / scale
        if x < 0 or y < 0 or x > iw or y > ih:
            return
        # Click = top-left of stamp box in image → convert to PDF bottom-left origin
        pdf_x = int(round(x / iw * self._pdf_w))
        pdf_top = int(round(y / ih * self._pdf_h))
        pdf_y = int(self._pdf_h) - pdf_top - self._box_h
        self._origin = self._clamp((pdf_x, pdf_y))
        self._repaint()

    @property
    def selected_pdf_xy(self) -> tuple[int, int] | None:
        return self._origin

    def _repaint(self) -> None:
        if self._img is None:
            return
        pix = self._img.copy()
        if self._origin:
            iw, ih = pix.width(), pix.height()
            # stamp box in image space (top-left origin)
            x0 = self._origin[0] / self._pdf_w * iw
            y0 = (1.0 - (self._origin[1] + self._box_h) / self._pdf_h) * ih
            w = self._box_w / self._pdf_w * iw
            h = self._box_h / self._pdf_h * ih
            painter = QPainter(pix)
            pen = QPen(QColor(30, 58, 95))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(30, 58, 95, 28))
            painter.drawRect(int(x0), int(y0), int(w), int(h))
            painter.end()
        self.setPixmap(
            QPixmap.fromImage(pix).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class SigPositionDialog(QDialog):
    def __init__(
        self,
        pdf_path: Path | None,
        *,
        page: int = 0,
        origin: tuple[int, int] | None = None,
        box_size: tuple[int, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vị trí ký")
        self.setMinimumSize(700, 620)
        self.setModal(True)
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._result: tuple[int, int, int] | None = None
        self._box_w = box_size[0] if box_size else DEFAULT_STAMP_W
        self._box_h = box_size[1] if box_size else DEFAULT_STAMP_H
        self._blank = self._pdf_path is None or not self._pdf_path.is_file()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        hint = (
            "Trang A4 mẫu (chưa thêm PDF) — bấm để đặt khung chữ ký:"
            if self._blank
            else "Bấm để đặt khung chữ ký (khung sẽ tự co lại cho vừa trang):"
        )
        root.addWidget(QLabel(hint))

        row = QHBoxLayout()
        row.addWidget(QLabel("Trang:"))
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(0)
        self._page_spin.setMaximum(0)
        if not self._blank:
            row.addWidget(self._page_spin)
        else:
            self._page_spin.hide()
            row.addWidget(QLabel("1 (A4)"))
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
        self._render()

    def _load_pages(self) -> None:
        if self._blank or self._pdf_path is None:
            self._page_spin.setMaximum(0)
            return
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(self._pdf_path))
            self._page_spin.setMaximum(max(0, len(doc) - 1))
            doc.close()
        except Exception:  # noqa: BLE001
            self._page_spin.setMaximum(0)

    def _render(self) -> None:
        from PySide6.QtGui import QImage

        # A4 in PDF points
        a4_w, a4_h = 595.0, 842.0
        try:
            if self._blank or self._pdf_path is None:
                # Virtual blank A4 page (no real PDF required)
                scale = 1.5
                iw, ih = int(a4_w * scale), int(a4_h * scale)
                qimg = QImage(iw, ih, QImage.Format.Format_RGB32)
                qimg.fill(Qt.GlobalColor.white)
                self._preview.set_page(
                    qimg, a4_w, a4_h, origin=self._origin,
                    box_w=self._box_w, box_h=self._box_h,
                )
            else:
                import pypdfium2 as pdfium

                doc = pdfium.PdfDocument(str(self._pdf_path))
                page = doc[self._page_spin.value()]
                w, h = page.get_size()
                bitmap = page.render(scale=1.5)
                img = bitmap.to_pil().convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(
                    data, img.width, img.height, QImage.Format.Format_RGBA8888
                ).copy()
                self._preview.set_page(
                    qimg, float(w), float(h),
                    origin=self._origin, box_w=self._box_w, box_h=self._box_h,
                )
                doc.close()
            if self._preview.selected_pdf_xy:
                x, y = self._preview.selected_pdf_xy
                page_no = 0 if self._blank else self._page_spin.value()
                self._pos_label.setText(f"({x}, {y}) trang {page_no + 1}")
        except Exception as exc:  # noqa: BLE001
            self._pos_label.setText(f"Lỗi preview: {exc}")

    def _reset_default(self) -> None:
        self._origin = (40, 40)
        self._pos_label.setText("Mặc định (40, 40)")
        self._render()

    def _accept(self) -> None:
        xy = self._preview.selected_pdf_xy
        page = self._page_spin.value()
        self._result = (page, xy[0], xy[1]) if xy else (page, 40, 40)
        self.accept()

    def result_position(self) -> tuple[int, int, int] | None:
        return self._result
