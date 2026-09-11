"""List / edit / delete per-certificate signing profiles."""

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

from golden_signing.storage.cert_profiles import CertProfile, CertProfileStore

__all__ = ["ProfilesDialog"]


class ProfilesDialog(QDialog):
    def __init__(self, store: CertProfileStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self.setWindowTitle("Hồ sơ ký")
        self.setMinimumSize(720, 400)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(8)
        root.addWidget(
            QLabel("Hồ sơ theo chứng thư số — chỉnh màu / logo / nền / vị trí / chế độ:")
        )

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Chủ thể", "Màu", "Logo", "Nền", "Chế độ"])
        self._table.setWordWrap(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

        actions = QHBoxLayout()
        self._count = QLabel("")
        refresh = QPushButton("Làm mới")
        edit = QPushButton("Chỉnh sửa…")
        delete = QPushButton("Xóa đã chọn")
        refresh.clicked.connect(self._reload)
        edit.clicked.connect(self._edit_selected)
        delete.clicked.connect(self._delete_selected)
        actions.addWidget(self._count)
        actions.addStretch(1)
        actions.addWidget(refresh)
        actions.addWidget(edit)
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
            company = p.company or p.fingerprint[:24]
            name_item = QTableWidgetItem(company)
            name_item.setData(Qt.ItemDataRole.UserRole, p.fingerprint)
            name_item.setToolTip(company)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(p.text_color_key))
            logo = "Có" if (p.show_logo and p.logo_path) else "—"
            item = QTableWidgetItem(logo)
            if p.logo_path:
                item.setToolTip(p.logo_path)
            self._table.setItem(row, 2, item)
            self._table.setItem(row, 3, QTableWidgetItem("Có" if p.show_background else "—"))
            self._table.setItem(row, 4, QTableWidgetItem(p.signature_mode))
            self._table.setRowHeight(row, 36)

    def _selected_fingerprint(self) -> str | None:
        rows = self._table.selectionModel().selectedRows() if self._table.selectionModel() else []
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if not item:
            return None
        fp = item.data(Qt.ItemDataRole.UserRole)
        return str(fp) if fp else None

    def _edit_selected(self) -> None:
        fp = self._selected_fingerprint()
        if not fp:
            QMessageBox.information(self, "Hồ sơ ký", "Chọn một hồ sơ để chỉnh sửa.")
            return
        prof = self._store.get(fp)
        if prof is None:
            return
        from golden_signing.ui.sign_settings_dialog import SignSettingsDialog

        sample = None
        # optional PDF for position preview — user can pick via dialog if needed
        dlg = SignSettingsDialog(
            mode=prof.signature_mode,
            color_key=prof.text_color_key,
            show_bg=prof.show_background,
            show_logo=bool(prof.show_logo and prof.logo_path),
            logo_path=prof.logo_path,
            sig_page=prof.sig_page or 0,
            sig_origin=(
                (int(prof.sig_x), int(prof.sig_y))
                if prof.sig_x is not None and prof.sig_y is not None
                else None
            ),
            sample_pdf=sample,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        r = dlg.values()
        updated = CertProfile(
            fingerprint=fp,
            company=prof.company,
            text_color_key=str(r["color_key"]),
            show_logo=bool(r["show_logo"] and r["logo_path"]),
            logo_path=str(r["logo_path"]) if r["show_logo"] else "",
            show_background=bool(r["show_bg"]),
            signature_mode=str(r["mode"]),
            sig_page=int(r["sig_page"] or 0),
            sig_x=float(r["sig_origin"][0]) if r.get("sig_origin") else None,
            sig_y=float(r["sig_origin"][1]) if r.get("sig_origin") else None,
        )
        self._store.upsert(updated)
        self._reload()

    def _delete_selected(self) -> None:
        fp = self._selected_fingerprint()
        if not fp:
            QMessageBox.information(self, "Hồ sơ ký", "Chọn ít nhất một dòng.")
            return
        ret = QMessageBox.question(
            self,
            "Xóa hồ sơ",
            "Xóa hồ sơ đã chọn?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        keep = [p for p in self._store.all() if p.fingerprint != fp]
        import json

        payload = {"version": 1, "profiles": {p.fingerprint: p.to_dict() for p in keep}}
        try:
            self._store.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._store._data.clear()  # noqa: SLF001
            for p in keep:
                self._store._data[p.fingerprint] = p  # noqa: SLF001
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
        self._reload()
