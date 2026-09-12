"""Settings dialog for Golden Signing."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from golden_signing.signing.appearance import DEFAULT_TEXT_COLORS
from golden_signing.storage.cert_profiles import CertProfileStore

__all__ = ["SettingsDialog"]

_COLOR_LABELS = {
    "navy": "Xanh navy",
    "black": "Đen",
    "dark_blue": "Xanh đậm",
    "forest": "Xanh rêu",
    "burgundy": "Đỏ mận",
    "gray": "Xám",
}


class SettingsDialog(QDialog):
    """Application defaults (not per-certificate profiles)."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
        self._settings = settings
        self.setWindowTitle("Cài đặt")
        self.setMinimumWidth(480)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        # Default output folder
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit(str(settings.value("defaultOutputDir", "") or ""))
        self._out_edit.setPlaceholderText("Trống = signed cạnh file nguồn")
        browse = QPushButton("Chọn…")
        browse.clicked.connect(self._browse_out)
        out_row.addWidget(self._out_edit, stretch=1)
        out_row.addWidget(browse)
        wrap = QWidget()
        wrap.setLayout(out_row)
        form.addRow("Thư mục output mặc định", wrap)

        # Signature mode default
        self._mode = QComboBox()
        self._mode.addItem("Hiển thị trên PDF", "visible")
        self._mode.addItem("Vô hình", "invisible")
        saved_mode = str(settings.value("defaultSignatureMode", "visible"))
        idx = 0 if saved_mode != "invisible" else 1
        self._mode.setCurrentIndex(idx)
        form.addRow("Chế độ ký mặc định", self._mode)

        # Text color default
        self._color = QComboBox()
        saved_color = str(settings.value("signatureTextColor", "navy"))
        for key in DEFAULT_TEXT_COLORS:
            self._color.addItem(_COLOR_LABELS.get(key, key), key)
            if key == saved_color:
                self._color.setCurrentIndex(self._color.count() - 1)
        form.addRow("Màu chữ mặc định", self._color)

        self._bg = QCheckBox("Nền nhạt khu vực chữ ký")
        self._bg.setChecked(str(settings.value("signatureBg", "1")) not in ("0", "false", "False"))
        form.addRow("", self._bg)

        self._autoscan = QCheckBox("Tự quét USB token khi mở app")
        self._autoscan.setChecked(
            str(settings.value("autoScanToken", "1")) not in ("0", "false", "False")
        )
        form.addRow("", self._autoscan)

        self._auto_update = QCheckBox("Tự kiểm tra cập nhật khi mở app")
        self._auto_update.setChecked(
            str(settings.value("autoCheckUpdate", "1")) not in ("0", "false", "False")
        )
        form.addRow("", self._auto_update)

        from golden_signing.updater.check import DEFAULT_UPDATE_REPO

        repo_val = str(settings.value("update/repo", "") or "")
        self._repo = QLineEdit(repo_val)
        self._repo.setPlaceholderText(f"mặc định {DEFAULT_UPDATE_REPO}")
        form.addRow("GitHub repo cập nhật", self._repo)

        root.addLayout(form)

        # Cert profiles
        root.addWidget(QLabel("Hồ sơ theo chứng thư (logo / màu / nền…):"))
        prof_row = QHBoxLayout()
        self._store = CertProfileStore()
        self._prof_count = QLabel(f"{len(self._store.all())} hồ sơ đã lưu")
        clear_btn = QPushButton("Xóa tất cả hồ sơ")
        clear_btn.clicked.connect(self._clear_profiles)
        open_btn = QPushButton("Mở thư mục")
        open_btn.clicked.connect(self._open_store_dir)
        prof_row.addWidget(self._prof_count)
        prof_row.addStretch(1)
        prof_row.addWidget(open_btn)
        prof_row.addWidget(clear_btn)
        root.addLayout(prof_row)

        note = QLabel(
            "Hồ sơ theo chứng thư: khi chọn token → tự load; chỉnh màu/logo/nền → tự lưu theo fingerprint."
        )
        note.setObjectName("productSub")
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_out(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục output mặc định")
        if folder:
            self._out_edit.setText(folder)

    def _clear_profiles(self) -> None:
        ret = QMessageBox.question(
            self,
            "Xóa hồ sơ",
            "Xóa toàn bộ hồ sơ theo chứng thư? (không ảnh hưởng file PDF)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            self._store.path.write_text('{"version":1,"profiles":{}}', encoding="utf-8")
            self._store._data.clear()  # noqa: SLF001
            self._prof_count.setText("0 hồ sơ đã lưu")
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _open_store_dir(self) -> None:
        import os
        import subprocess
        import sys

        d = self._store.path.parent
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(d)])
            else:
                os.startfile(str(d))  # noqa: S606
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _save(self) -> None:
        s = self._settings
        s.setValue("defaultOutputDir", self._out_edit.text().strip())
        s.setValue("defaultSignatureMode", self._mode.currentData())
        s.setValue("signatureTextColor", self._color.currentData())
        s.setValue("signatureBg", "1" if self._bg.isChecked() else "0")
        s.setValue("autoScanToken", "1" if self._autoscan.isChecked() else "0")
        s.setValue("autoCheckUpdate", "1" if self._auto_update.isChecked() else "0")
        s.setValue("update/repo", self._repo.text().strip())
        self.accept()
