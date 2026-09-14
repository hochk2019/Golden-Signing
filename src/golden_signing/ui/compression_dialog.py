"""Compression settings dialog (v1.1)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from golden_signing.compress.engine import CompressionProfile, CompressionTier, default_profile

__all__ = ["CompressionSettingsDialog"]


class CompressionSettingsDialog(QDialog):
    def __init__(
        self,
        profile: CompressionProfile | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
        self.setWindowTitle("Cài đặt nén PDF")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._profile = profile or CompressionProfile()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self._tier = QComboBox()
        self._tier.addItem(
            "Không nén ảnh (lossless) — giữ nguyên chất lượng",
            CompressionTier.LOSSLESS.value,
        )
        self._tier.addItem(
            "Cân bằng — JPEG ~85 · DPI ≤200",
            CompressionTier.BALANCED.value,
        )
        self._tier.addItem(
            "PUS Safe — mục tiêu ≤400 KB",
            CompressionTier.PUS_SAFE.value,
        )
        self._tier.addItem(
            "Tùy chỉnh — tự đặt target / JPEG / DPI",
            CompressionTier.CUSTOM.value,
        )
        for i in range(self._tier.count()):
            if self._tier.itemData(i) == self._profile.tier:
                self._tier.setCurrentIndex(i)
                break
        self._tier.currentIndexChanged.connect(self._on_tier)
        form.addRow("Profile", self._tier)

        self._target_kb = QSpinBox()
        self._target_kb.setRange(50, 50_000)
        self._target_kb.setSuffix(" KB")
        self._target_kb.setValue((self._profile.target_bytes or 400 * 1024) // 1024)
        form.addRow("Mục tiêu (trước ký)", self._target_kb)

        self._reserve_kb = QSpinBox()
        self._reserve_kb.setRange(0, 1024)
        self._reserve_kb.setSuffix(" KB")
        self._reserve_kb.setValue(self._profile.signature_reserve_bytes // 1024)
        form.addRow("Dự phòng chữ ký", self._reserve_kb)

        self._quality = QSpinBox()
        self._quality.setRange(40, 95)
        self._quality.setValue(self._profile.jpeg_quality)
        form.addRow("JPEG quality", self._quality)

        self._dpi = QSpinBox()
        self._dpi.setRange(72, 300)
        self._dpi.setValue(self._profile.max_dpi)
        form.addRow("DPI ảnh tối đa", self._dpi)

        self._downsample = QCheckBox("Giảm kích thước ảnh lớn")
        self._downsample.setChecked(self._profile.downsample)
        form.addRow("", self._downsample)

        self._strip_meta = QCheckBox("Xóa metadata không cần thiết")
        self._strip_meta.setChecked(self._profile.strip_metadata)
        form.addRow("", self._strip_meta)

        self._name = QLineEdit(self._profile.name)
        form.addRow("Tên profile", self._name)
        root.addLayout(form)

        note = QLabel(
            "Nén chạy TRƯỚC khi ký. File đã có chữ ký sẽ không bị nén.\n"
            "Không phải mọi PDF đều đạt mục tiêu — sẽ giữ sàn chất lượng."
        )
        note.setObjectName("productSub")
        note.setWordWrap(True)
        root.addWidget(note)

        row = QHBoxLayout()
        reset_btn = QPushButton("Mặc định")
        reset_btn.setObjectName("btnSecondary")
        reset_btn.clicked.connect(self._reset)
        row.addWidget(reset_btn)
        row.addStretch(1)
        root.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._on_tier()

    def _on_tier(self) -> None:
        tier = str(self._tier.currentData())
        custom = tier == CompressionTier.CUSTOM.value
        lossless = tier == CompressionTier.LOSSLESS.value
        # Load distinct preset numbers when switching profile
        p = default_profile(CompressionTier(tier))  # type: ignore[arg-type]
        self._target_kb.setEnabled(custom or tier == CompressionTier.PUS_SAFE.value)
        self._quality.setEnabled(not lossless)
        self._dpi.setEnabled(not lossless)
        self._downsample.setEnabled(not lossless)
        if p.target_bytes:
            self._target_kb.setValue(p.target_bytes // 1024)
        self._reserve_kb.setValue(p.signature_reserve_bytes // 1024)
        self._quality.setValue(p.jpeg_quality)
        self._dpi.setValue(p.max_dpi)
        self._downsample.setChecked(p.downsample)
        self._strip_meta.setChecked(p.strip_metadata)
        # Only auto-rename when still on a stock name
        stock = {
            "PUS Safe 400KB",
            "Lossless",
            "Balanced",
            "Custom",
            "Không nén ảnh (lossless)",
            "Cân bằng (chất lượng tốt)",
            "Tùy chỉnh",
            "PUS Safe — mục tiêu ≤400 KB",
        }
        if self._name.text().strip() in stock or not self._name.text().strip():
            self._name.setText(p.name)

    def _reset(self) -> None:
        self._tier.setCurrentIndex(2)  # PUS Safe
        p = default_profile(CompressionTier.PUS_SAFE)
        self._target_kb.setValue((p.target_bytes or 400 * 1024) // 1024)
        self._reserve_kb.setValue(p.signature_reserve_bytes // 1024)
        self._quality.setValue(p.jpeg_quality)
        self._dpi.setValue(p.max_dpi)
        self._downsample.setChecked(p.downsample)
        self._strip_meta.setChecked(p.strip_metadata)
        self._name.setText(p.name)

    def profile(self) -> CompressionProfile:
        tier = str(self._tier.currentData())
        if tier in (CompressionTier.LOSSLESS.value, CompressionTier.BALANCED.value):
            target_val: int | None = None
        else:
            target_val = self._target_kb.value() * 1024
        return CompressionProfile(
            name=self._name.text().strip() or "Custom",
            tier=tier,
            target_bytes=target_val,
            signature_reserve_bytes=self._reserve_kb.value() * 1024,
            jpeg_quality=self._quality.value(),
            max_dpi=self._dpi.value(),
            downsample=self._downsample.isChecked(),
            strip_metadata=self._strip_meta.isChecked(),
        )
