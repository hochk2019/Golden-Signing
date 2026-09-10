"""List / manage per-certificate signing profiles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from golden_signing.storage.cert_profiles import CertProfileStore
from golden_signing.ui.cert_label import common_name_from_subject

__all__ = ["ProfilesDialog"]


class ProfilesDialog(QDialog):
    def __init__(self, store: CertProfileStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self.setWindowTitle("Hồ sơ ký")
        self.setMinimumSize(640, 360)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(8)
        root.addWidget(QLabel("Hồ sơ theo chứng thư số (tự lưu khi bạn chỉnh màu / logo / nền):"))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Chủ thể", "Màu", "Logo", "Nền", "Chế độ"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self._table, stretch=1)

        actions = QHBoxLayout()
        self._count = QLabel("")
        refresh = QPushButton("Làm mới")
        delete = QPushButton("Xóa đã chọn")
        refresh.clicked.connect(self._reload)
        delete.clicked.connect(self._delete_selected)
        actions.addWidget(self._count)
        actions.addStretch(1)
        actions.addWidget(refresh)
        actions.addWidget(delete)
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
        self._reload()

    def _reload(self) -> None:
        items = self._store.all()
        self._count.setText(f"{len(items)} hồ sơ · {self._store.path}")
        self._table.setRowCount(len(items))
        for row, p in enumerate(items):
            company = p.company or common_name_from_subject(p.company) or p.fingerprint[:16]
            name_item = QTableWidgetItem(company)
            name_item.setData(Qt.ItemDataRole.UserRole, p.fingerprint)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(p.text_color_key))
            logo = "Có" if (p.show_logo and p.logo_path) else "—"
            item = QTableWidgetItem(logo)
            if p.logo_path:
                item.setToolTip(p.logo_path)
            self._table.setItem(row, 2, item)
            self._table.setItem(row, 3, QTableWidgetItem("Có" if p.show_background else "—"))
            self._table.setItem(row, 4, QTableWidgetItem(p.signature_mode))

    def _delete_selected(self) -> None:
        rows = sorted((i.row() for i in self._table.selectionModel().selectedRows()), reverse=True)
        if not rows:
            QMessageBox.information(self, "Hồ sơ ký", "Chọn ít nhất một dòng.")
            return
        ret = QMessageBox.question(
            self,
            "Xóa hồ sơ",
            f"Xóa {len(rows)} hồ sơ đã chọn?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        # rewrite store without selected fingerprints
        selected = set()
        for r in rows:
            item = self._table.item(r, 0)
            if item:
                fp = item.data(Qt.ItemDataRole.UserRole)
                if fp:
                    selected.add(str(fp))
        keep = [p for p in self._store.all() if p.fingerprint not in selected]
        try:
            import json

            payload = {
                "version": 1,
                "profiles": {p.fingerprint: p.to_dict() for p in keep},
            }
            self._store.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._store._data.clear()  # noqa: SLF001
            for p in keep:
                self._store._data[p.fingerprint] = p  # noqa: SLF001
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
        self._reload()
