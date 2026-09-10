"""History list dialog."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from golden_signing.storage.history import SigningHistory

__all__ = ["HistoryDialog"]


class HistoryDialog(QDialog):
    def __init__(self, history: SigningHistory, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._history = history
        self.setWindowTitle("Lịch sử ký")
        self.setMinimumSize(720, 400)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(8)
        root.addWidget(QLabel(f"Cơ sở dữ liệu: {history.path}"))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Thời gian", "Trạng thái", "File", "Output", "Lỗi"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

        row = QHBoxLayout()
        refresh = QPushButton("Làm mới")
        export = QPushButton("Export CSV…")
        refresh.clicked.connect(self._reload)
        export.clicked.connect(self._export)
        row.addStretch(1)
        row.addWidget(refresh)
        row.addWidget(export)
        root.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
        self._reload()

    def _reload(self) -> None:
        items = self._history.recent(300)
        self._table.setRowCount(len(items))
        for row, rec in enumerate(items):
            ts = datetime.fromtimestamp(rec.ts).strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(row, 0, QTableWidgetItem(ts))
            self._table.setItem(row, 1, QTableWidgetItem(rec.status))
            self._table.setItem(row, 2, QTableWidgetItem(Path_name(rec.input_path)))
            self._table.setItem(row, 3, QTableWidgetItem(Path_name(rec.output_path or "")))
            self._table.setItem(row, 4, QTableWidgetItem(rec.error_code or ""))

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export lịch sử", "history.csv", "CSV (*.csv)")
        if not path:
            return
        out = self._history.export_csv(Path(path))
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Export", f"Đã ghi: {out}")


def Path_name(p: str) -> str:  # noqa: N802
    from pathlib import Path

    return Path(p).name if p else ""
