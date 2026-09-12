"""Show detailed error for a failed signing job."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from golden_signing.batch.state import SigningJob

__all__ = ["JobErrorDialog"]


class JobErrorDialog(QDialog):
    def __init__(self, job: SigningJob, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
        self.setWindowTitle("Chi tiết lỗi")
        self.setMinimumSize(480, 280)
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.addWidget(QLabel(f"File: {job.input_path.name}"))
        lay.addWidget(QLabel(f"Trạng thái: {job.state.value}"))
        if job.error_code:
            lay.addWidget(QLabel(f"Mã lỗi: {job.error_code}"))
        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(job.message or "(không có thông điệp)")
        lay.addWidget(body, stretch=1)
        row = QHBoxLayout()
        if job.output_path:
            open_btn = QPushButton("Mở file")
            open_btn.clicked.connect(lambda: self._open(str(job.output_path)))
            row.addWidget(open_btn)
        row.addStretch(1)
        lay.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        lay.addWidget(buttons)

    def _open(self, path: str) -> None:
        import os
        import subprocess
        import sys
        from pathlib import Path

        try:
            if sys.platform.startswith("win"):
                if Path(path).is_file():
                    os.startfile(path)  # noqa: S606
                else:
                    subprocess.Popen(["explorer", path])
        except Exception:  # noqa: BLE001
            pass
