"""Golden Signing main window — token-aware Phase 5 UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from golden_signing.batch.queue import BatchEngine
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile
from golden_signing.signing.token_pdf_signer import TokenPdfSigner
from golden_signing.token.discovery import discover_pkcs11_libraries
from golden_signing.ui.file_table import FileJobTableModel
from golden_signing.ui.theme import apply_theme

__all__ = ["MainWindow"]


def _brand_mark_path() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[3]
    return root / "assets" / "branding" / "golden-mark.png"


class CertPickerDialog(QDialog):
    """Compact cert chooser — short CN + expiry only."""

    def __init__(self, certs: list, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chọn chứng thư số")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)

        hint = QLabel("Chứng thư trên USB token:")
        lay.addWidget(hint)
        self._combo = QComboBox()
        self._combo.setMinimumHeight(32)
        for c in certs:
            self._combo.addItem(_short_cert_label(c), userData=c)
        lay.addWidget(self._combo)

        self._detail = QLabel()
        self._detail.setObjectName("productSub")
        self._detail.setWordWrap(True)
        self._detail.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self._detail)
        self._combo.currentIndexChanged.connect(self._on_index_changed)
        if certs:
            self._on_index_changed(0)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Chọn")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _on_index_changed(self, index: int) -> None:
        c = self._combo.itemData(index)
        if c is None:
            self._detail.setText("")
            return
        expiry = str(c.not_valid_after)[:10]
        self._detail.setText(f"Issuer: {_ellipsis(c.issuer, 48)}\nHết hạn: {expiry}")

    def selected_cert(self):  # noqa: ANN201
        return self._combo.currentData()


def _ellipsis(text: str, n: int) -> str:
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _short_cert_label(cert) -> str:  # noqa: ANN001
    """Prefer CN=... from subject; fallback first 40 chars."""
    subject = str(getattr(cert, "subject", "") or "")
    cn = ""
    for part in subject.split(","):
        part = part.strip()
        if part.upper().startswith("CN=") or part.upper().startswith("COMMON NAME:"):
            cn = part.split(":", 1)[-1].strip() if ":" in part else part[3:].strip()
            break
    if not cn:
        # Vietnamese certs often put company name after Common Name:
        if "Common Name:" in subject:
            cn = subject.split("Common Name:", 1)[1].split(",")[0].strip()
        else:
            cn = subject[:40]
    expiry = str(getattr(cert, "not_valid_after", ""))[:10]
    token = getattr(cert, "token_label", None) or ""
    base = _ellipsis(cn, 36)
    if token:
        return f"{base} · {token} · {expiry}"
    return f"{base} · {expiry}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golden Signing — Ký số PDF")
        self.resize(960, 640)
        self.setAcceptDrops(True)

        self._model = FileJobTableModel(self)
        self._token_signer: TokenPdfSigner | None = None
        self._lab_signer: TestCertPdfSigner | None = None
        self._nav_buttons: list[QPushButton] = []

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_rail())
        root.addWidget(self._build_workspace(), stretch=1)
        self.setCentralWidget(central)
        self._update_summary()
        self._sign_btn.setEnabled(False)
        self._token_note.setText("Đang quét USB token…")
        # Auto-scan shortly after show (list certs only — no PIN).
        from PySide6.QtCore import QTimer

        QTimer.singleShot(400, self._refresh_token_label)

    def _build_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(220)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(8)

        mark = QLabel()
        mark_path = _brand_mark_path()
        if mark_path.is_file():
            from PySide6.QtGui import QPixmap

            pix = QPixmap(str(mark_path)).scaled(
                40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            mark.setPixmap(pix)
        mark.setFixedHeight(40)
        lay.addWidget(mark)

        title = QLabel("Golden Signing")
        title.setObjectName("productTitle")
        sub = QLabel("Ký số PDF")
        sub.setObjectName("productSub")
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addSpacing(16)

        for label, handler in (
            ("Ký tài liệu", self._nav_sign_docs),
            ("Hồ sơ ký", self._nav_profiles),
            ("Cài đặt", self._nav_settings),
            ("Giới thiệu", self._nav_about),
        ):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            self._nav_buttons.append(btn)
            lay.addWidget(btn)
        lay.addStretch(1)
        self._token_note = QLabel("Đang kiểm tra token…")
        self._token_note.setObjectName("productSub")
        self._token_note.setWordWrap(True)
        lay.addWidget(self._token_note)
        return rail

    def _build_workspace(self) -> QWidget:
        ws = QWidget()
        lay = QVBoxLayout(ws)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        header = QLabel("Ký tài liệu")
        header.setObjectName("productTitle")
        lay.addWidget(header)

        drop = QLabel("Kéo thả PDF vào đây")
        drop.setObjectName("dropHint")
        drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(drop)

        actions = QHBoxLayout()
        self._add_btn = QPushButton("Thêm PDF")
        self._add_dir_btn = QPushButton("Thêm thư mục")
        self._rescan_btn = QPushButton("Quét lại token")
        self._add_btn.clicked.connect(self._on_add_files)
        self._add_dir_btn.clicked.connect(self._on_add_folder)
        self._rescan_btn.clicked.connect(self._on_rescan_token)
        actions.addWidget(self._add_btn)
        actions.addWidget(self._add_dir_btn)
        actions.addWidget(self._rescan_btn)
        actions.addStretch(1)
        self._profile_label = QLabel("Profile: PUS Safe")
        self._profile_label.setObjectName("goldAccent")
        actions.addWidget(self._profile_label)
        lay.addLayout(actions)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Tên file", "Trạng thái", "Thông điệp"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self._table, stretch=1)

        # Output folder
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Thư mục output:"))
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Để trống → thư mục signed cạnh file nguồn")
        self._out_edit.setClearButtonEnabled(True)
        out_row.addWidget(self._out_edit, stretch=1)
        self._out_browse = QPushButton("Chọn…")
        self._out_browse.clicked.connect(self._on_choose_output_dir)
        out_row.addWidget(self._out_browse)
        lay.addLayout(out_row)

        # Signature mode
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Hiển thị chữ ký số:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Vô hình — không đổi giao diện", userData="invisible")
        self._mode_combo.addItem("Hiển thị trên PDF", userData="visible")
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch(1)
        self._open_folder_btn = QPushButton("Mở thư mục")
        self._open_file_btn = QPushButton("Mở file đã chọn")
        self._clear_btn = QPushButton("Xóa khỏi danh sách")
        self._open_folder_btn.clicked.connect(self._on_open_output_folder)
        self._open_file_btn.clicked.connect(self._on_open_signed_file)
        self._clear_btn.clicked.connect(self._on_clear_selected)
        mode_row.addWidget(self._open_folder_btn)
        mode_row.addWidget(self._open_file_btn)
        mode_row.addWidget(self._clear_btn)
        lay.addLayout(mode_row)

        footer = QHBoxLayout()
        self._summary = QLabel("0 file")
        footer.addWidget(self._summary)
        footer.addStretch(1)
        self._sign_btn = QPushButton("KÝ SỐ")
        self._sign_btn.setObjectName("primaryCta")
        self._sign_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sign_btn.clicked.connect(self._on_sign)
        footer.addWidget(self._sign_btn)
        lay.addLayout(footer)
        return ws

    def _on_choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file đã ký")
        if folder:
            self._out_edit.setText(folder)

    def _resolve_output_dir(self, jobs: list) -> Path:
        text = self._out_edit.text().strip()
        if text:
            return Path(text)
        if jobs:
            return jobs[0].input_path.parent / "signed"
        return Path.cwd() / "signed"

    def _on_open_output_folder(self) -> None:
        jobs = self._model.jobs()
        folder = self._resolve_output_dir(jobs)
        folder.mkdir(parents=True, exist_ok=True)
        self._open_path(folder)

    def _on_open_signed_file(self) -> None:
        rows = self._table.selectionModel().selectedRows() if self._table.selectionModel() else []
        if not rows:
            QMessageBox.information(self, "Golden Signing", "Hãy chọn một dòng trong danh sách.")
            return
        job = self._model.jobs()[rows[0].row()]
        target = job.output_path
        if target is None or not Path(target).exists():
            QMessageBox.warning(self, "Golden Signing", "File đã ký chưa tồn tại cho dòng này.")
            return
        self._open_path(Path(target))

    def _on_clear_selected(self) -> None:
        rows = sorted(
            (i.row() for i in self._table.selectionModel().selectedRows()),
            reverse=True,
        ) if self._table.selectionModel() else []
        if not rows:
            # clear all
            self._model.replace_jobs([])
            self._reload_table()
            self._update_summary()
            return
        jobs = self._model.jobs()
        keep = [j for idx, j in enumerate(jobs) if idx not in set(rows)]
        self._model.replace_jobs(keep)
        self._reload_table()
        self._update_summary()

    def _open_path(self, path: Path) -> None:
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("win"):
                if path.is_file():
                    os.startfile(str(path))  # noqa: S606
                else:
                    subprocess.Popen(["explorer", str(path)])
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, str(path)])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Golden Signing", f"Không mở được:\n{exc}")

    # --- nav stubs ----------------------------------------------------

    def _nav_sign_docs(self) -> None:
        self.statusBar().showMessage("Đang ở màn Ký tài liệu", 3000)

    def _nav_profiles(self) -> None:
        QMessageBox.information(
            self,
            "Hồ sơ ký",
            "Hồ sơ ký sẽ gắn theo chứng thư (Phase 6).\nHiện dùng profile PUS Safe mặc định.",
        )

    def _nav_settings(self) -> None:
        QMessageBox.information(self, "Cài đặt", "Cài đặt chi tiết sẽ bổ sung ở phase sau.")

    def _nav_about(self) -> None:
        QMessageBox.information(
            self,
            "Giới thiệu",
            "Golden Signing\nPDF Digital Signature Utility\n"
            "Developer: HOC HK\nhochk2019@gmail.com · 0868.333.606\n"
            "Phiên bản 0.1.0-alpha\n\n"
            "Miễn trừ: công cụ hỗ trợ ký số; không đảm bảo mọi hệ thống bên thứ ba chấp nhận.",
        )

    # --- token --------------------------------------------------------

    def _refresh_token_label(self) -> None:
        dlls = discover_pkcs11_libraries()
        if not dlls:
            self._token_note.setText("Chưa tìm thấy PKCS#11.\nCó thể ký bằng lab cert (test).")
            return
        try:
            certs = TokenPdfSigner.list_certificates(dlls[0])
            if certs:
                c = certs[0]
                self._token_note.setText(
                    f"Token: {c.token_label or 'USB'}\n{c.subject[:48]}…"
                )
                self._profile_label.setText("Profile: PUS Safe · Token USB")
            else:
                self._token_note.setText(f"PKCS#11: {dlls[0].name}\nChưa thấy chứng thư.")
        except Exception as exc:  # noqa: BLE001
            self._token_note.setText(f"Token lỗi: {exc}\nCó thể thử lab cert.")

    def _on_rescan_token(self) -> None:
        self._token_signer = None
        self._refresh_token_label()
        self.statusBar().showMessage("Đã quét lại token", 3000)

    def _ensure_token_engine(self) -> TokenPdfSigner | None:
        dlls = discover_pkcs11_libraries()
        if not dlls:
            return None
        dll = dlls[0]
        try:
            certs = TokenPdfSigner.list_certificates(dll)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Token", f"Không đọc được token:\n{exc}")
            return None
        if not certs:
            QMessageBox.warning(self, "Token", "Token không có chứng thư số.")
            return None
        dlg = CertPickerDialog(certs, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        chosen = dlg.selected_cert()
        if chosen is None:
            return None
        pin, ok = QInputDialog.getText(
            self,
            "PIN chữ ký số",
            "PIN (không lưu):",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not pin:
            return None
        try:
            session, asn1_cert = TokenPdfSigner.open_session_with_pin(
                dll,
                pin,
                cert_serial=getattr(chosen, "serial", None),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Token", f"Đăng nhập token thất bại:\n{exc}")
            return None
        finally:
            pin = ""  # noqa: PLW0642 — drop local ref
        signer = TokenPdfSigner(dll)
        signer.bind_session(session, asn1_cert)
        if getattr(chosen, "fingerprint_sha256", ""):
            signer.certificate_fingerprint_sha256 = chosen.fingerprint_sha256
        self._token_signer = signer
        self._profile_label.setText(f"Profile: PUS Safe · {_ellipsis(chosen.subject, 32)}")
        self._token_note.setText(
            f"Đã kết nối: {_ellipsis(chosen.subject, 40)}\nToken: {chosen.token_label or 'USB'}"
        )
        return signer

    # --- files / drag -------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        self.add_paths(paths)
        event.acceptProposedAction()

    def add_paths(self, paths: list[Path]) -> None:
        files: list[Path] = []
        for p in paths:
            if p.is_dir():
                files.extend(sorted(p.glob("*.pdf")))
            elif p.is_file():
                files.append(p)
        before = self._model.rowCount()
        self._model.add_paths(files)
        if self._model.rowCount() != before:
            self._reload_table()
        self._update_summary()

    def _reload_table(self) -> None:
        jobs = self._model.jobs()
        self._table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            self._table.setItem(row, 0, QTableWidgetItem(job.input_path.name))
            self._table.setItem(row, 1, QTableWidgetItem(job.state.value))
            self._table.setItem(row, 2, QTableWidgetItem(job.message))

    def _update_summary(self) -> None:
        total, ok, err = self._model.summary()
        self._summary.setText(f"{total} file · {ok} thành công · {err} lỗi")
        self._sign_btn.setEnabled(total > 0)

    def _on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn PDF", "", "PDF (*.pdf)")
        self.add_paths([Path(f) for f in files])

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder:
            self.add_paths([Path(folder)])

    # --- sign ---------------------------------------------------------

    def _on_sign(self) -> None:
        jobs = [j for j in self._model.jobs() if not j.is_terminal]
        if not jobs:
            QMessageBox.information(self, "Golden Signing", "Không có file chờ ký.")
            return

        engine = self._token_signer
        if engine is None:
            use_token = QMessageBox.question(
                self,
                "Chọn phương thức ký",
                "Thử ký bằng USB token (khuyến nghị)?\n"
                "Chọn No để dùng lab certificate (chỉ test).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if use_token == QMessageBox.StandardButton.Yes:
                engine = self._ensure_token_engine()
                if engine is None:
                    return
            else:
                if self._lab_signer is None:
                    self._lab_signer = TestCertPdfSigner()
                engine = self._lab_signer
                self._profile_label.setText("Profile: PUS Safe · lab (test cert)")

        profile = pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)
        mode_key = self._mode_combo.currentData() or "invisible"
        if mode_key == "visible":
            from golden_signing.signing.contracts import SignatureMode

            profile.mode = SignatureMode.VISIBLE
        out_dir = self._resolve_output_dir(jobs)
        batch = BatchEngine(
            engine,
            profile,
            output_dir=out_dir,
            on_progress=self._on_batch_progress,
        )
        batch.enqueue_jobs(jobs)
        self._sign_btn.setEnabled(False)
        try:
            result = batch.run()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Golden Signing", f"Lỗi khi ký:\n{exc}")
            self._sign_btn.setEnabled(True)
            return
        finally:
            self._sign_btn.setEnabled(True)

        self._model.replace_jobs(list(batch.jobs))
        self._reload_table()
        self._update_summary()

        failed_msgs = [f"{j.input_path.name}: {j.message}" for j in result.jobs if j.error_code]
        extra = ("\n\n" + "\n".join(failed_msgs[:5])) if failed_msgs else ""
        title = "Golden Signing"
        if result.failed:
            QMessageBox.warning(
                self,
                title,
                f"Hoàn tất: {result.success} thành công · {result.failed} lỗi · {result.cancelled} hủy\n"
                f"Thư mục: {out_dir}{extra}",
            )
        else:
            QMessageBox.information(
                self,
                title,
                f"Hoàn tất: {result.success} thành công · 0 lỗi\nThư mục: {out_dir}",
            )

    def _on_batch_progress(self, done: int, total: int, job: object) -> None:
        self._summary.setText(f"Đang ký {done}/{total}…")
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()


def run_app() -> int:
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()
