"""Popup: signature appearance settings (mode, color, bg, logo, position)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from golden_signing.signing.appearance import DEFAULT_TEXT_COLORS

__all__ = ["SignSettingsDialog"]

_COLOR_LABELS = {
    "navy": "Xanh navy",
    "black": "Đen",
    "dark_blue": "Xanh đậm",
    "forest": "Xanh rêu",
    "burgundy": "Đỏ mận",
    "gray": "Xám",
}


class SignSettingsDialog(QDialog):
    """Returns (mode, color_key, show_bg, show_logo, logo_path, page, x, y)."""

    def __init__(
        self,
        *,
        mode: str,
        color_key: str,
        show_bg: bool,
        show_logo: bool,
        logo_path: str,
        sig_page: int,
        sig_origin: tuple[int, int] | None,
        sample_pdf: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
        self.setWindowTitle("Cài đặt ký")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._sample_pdf = sample_pdf
        self._sig_page = sig_page
        self._sig_origin = sig_origin

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self._mode = QComboBox()
        self._mode.addItem("Hiển thị trên PDF", "visible")
        self._mode.addItem("Vô hình", "invisible")
        self._mode.setCurrentIndex(0 if mode == "visible" else 1)
        form.addRow("Chế độ ký", self._mode)

        self._color = QComboBox()
        for key in DEFAULT_TEXT_COLORS:
            self._color.addItem(_COLOR_LABELS.get(key, key), key)
            if key == color_key:
                self._color.setCurrentIndex(self._color.count() - 1)
        form.addRow("Màu chữ", self._color)

        self._bg = QCheckBox("Nền nhạt")
        self._bg.setChecked(show_bg)
        form.addRow("", self._bg)

        self._logo = QCheckBox("Hiện logo" if not show_logo else "Ẩn logo")
        self._logo.setChecked(show_logo)
        self._logo.setText("Ẩn logo" if show_logo else "Hiện logo")
        self._logo.toggled.connect(self._on_logo_toggled)
        form.addRow("", self._logo)

        logo_row = QHBoxLayout()
        self._logo_path_edit = QLabel(Path(logo_path).name if logo_path else "Chưa chọn logo")
        self._logo_path_edit.setObjectName("productSub")
        pick = QPushButton("Chọn logo…")
        pick.clicked.connect(self._pick_logo)
        logo_row.addWidget(self._logo_path_edit, stretch=1)
        logo_row.addWidget(pick)
        logo_wrap = QWidget()
        logo_wrap.setLayout(logo_row)
        form.addRow("Logo", logo_wrap)
        self._logo_path = logo_path

        pos_row = QHBoxLayout()
        pos_text = (
            f"Trang {sig_page + 1} ({sig_origin[0]}, {sig_origin[1]})"
            if sig_origin
            else "Mặc định (40, 40)"
        )
        self._pos_label = QLabel(pos_text)
        self._pos_label.setObjectName("productSub")
        pos_btn = QPushButton("Vị trí ký…")
        pos_btn.clicked.connect(self._pick_pos)
        pos_row.addWidget(self._pos_label, stretch=1)
        pos_row.addWidget(pos_btn)
        pos_wrap = QWidget()
        pos_wrap.setLayout(pos_row)
        form.addRow("Vị trí", pos_wrap)

        root.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_logo_toggled(self, checked: bool) -> None:
        self._logo.setText("Ẩn logo" if checked else "Hiện logo")

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn logo", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._logo_path = path
            self._logo_path_edit.setText(Path(path).name)
            self._logo.setChecked(True)
            self._logo.setText("Ẩn logo")

    def _pick_pos(self) -> None:
        sample = self._sample_pdf if (self._sample_pdf and self._sample_pdf.is_file()) else None
        from golden_signing.ui.sig_position_dialog import SigPositionDialog

        dlg = SigPositionDialog(
            sample, page=self._sig_page, origin=self._sig_origin, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        pos = dlg.result_position()
        if pos:
            self._sig_page, x, y = pos
            self._sig_origin = (x, y)
            self._pos_label.setText(f"Trang {self._sig_page + 1} ({x}, {y})")

    def values(self) -> dict[str, Any]:
        return {
            "mode": self._mode.currentData(),
            "color_key": self._color.currentData(),
            "show_bg": self._bg.isChecked(),
            "show_logo": self._logo.isChecked(),
            "logo_path": self._logo_path,
            "sig_page": self._sig_page,
            "sig_origin": self._sig_origin,
        }
