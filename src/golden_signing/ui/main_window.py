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
from golden_signing.signing.appearance import DEFAULT_TEXT_COLORS
from golden_signing.signing.contracts import SigningProfile
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile
from golden_signing.signing.token_pdf_signer import TokenPdfSigner
from golden_signing.storage.cert_profiles import CertProfile, CertProfileStore
from golden_signing.token.discovery import discover_pkcs11_libraries
from golden_signing.ui.cert_label import common_name_from_subject
from golden_signing.ui.file_table import FileJobTableModel
from golden_signing.ui.settings_dialog import SettingsDialog
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
        from golden_signing.ui.cert_label import cert_detail_lines

        self._detail.setText(cert_detail_lines(c))

    def selected_cert(self):  # noqa: ANN201
        return self._combo.currentData()


def _ellipsis(text: str, n: int) -> str:
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _short_cert_label(cert) -> str:  # noqa: ANN001
    """Short display: company CN · token · expiry (YYYY-MM-DD)."""
    from golden_signing.ui.cert_label import short_cert_label

    return short_cert_label(cert)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golden Signing — Ký số PDF")
        self.resize(1080, 700)
        self.setAcceptDrops(True)

        self._model = FileJobTableModel(self)
        self._token_signer: TokenPdfSigner | None = None
        self._lab_signer: TestCertPdfSigner | None = None
        self._nav_buttons: list[QPushButton] = []
        self._cert_store = CertProfileStore()
        self._active_fingerprint: str | None = None
        self._sig_origin: tuple[int, int] | None = None
        self._sig_page = 0
        self._batch_engine: BatchEngine | None = None
        self._batch_paused = False
        from golden_signing.storage.history import SigningHistory

        self._history = SigningHistory()
        from PySide6.QtCore import QSettings

        self._settings = QSettings("HOCHK", "GoldenSigning")

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
        from PySide6.QtCore import QTimer

        if str(self._settings.value("autoScanToken", "1")) not in ("0", "false", "False"):
            QTimer.singleShot(400, self._refresh_token_label)
        else:
            self._token_note.setText("Tự quét token đã tắt (Cài đặt).")
        self._load_app_defaults()

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
            ("Xác minh PDF", self._on_verify_pdf),
            ("Hồ sơ ký", self._nav_profiles),
            ("Lịch sử ký", self._nav_history),
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
        self._table.setHorizontalHeaderLabels(["Tên file", "Trạng thái", "Hành động"])
        tbl_header = self._table.horizontalHeader()
        if tbl_header is not None:
            tbl_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            tbl_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            tbl_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            tbl_header.setStretchLastSection(False)
        self._table.setColumnWidth(1, 96)
        self._table.setColumnWidth(2, 210)
        if tbl_header is not None:
            tbl_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
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

        # Hidden state widgets (edited via Cài đặt ký popup)
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Vô hình — không đổi giao diện", userData="invisible")
        self._mode_combo.addItem("Hiển thị trên PDF", userData="visible")
        self._select_mode(str(self._settings.value("defaultSignatureMode", "visible")))
        self._mode_combo.currentIndexChanged.connect(lambda _i: self._save_active_profile())
        self._mode_combo.hide()

        self._color_combo = QComboBox()
        color_labels = {
            "navy": "Xanh navy",
            "black": "Đen",
            "dark_blue": "Xanh đậm",
            "forest": "Xanh rêu",
            "burgundy": "Đỏ mận",
            "gray": "Xám",
        }
        for key, rgb in DEFAULT_TEXT_COLORS.items():
            self._color_combo.addItem(color_labels.get(key, key), userData=(key, rgb))
        saved_key = str(self._settings.value("signatureTextColor", "navy"))
        for i in range(self._color_combo.count()):
            item = self._color_combo.itemData(i)
            if item and item[0] == saved_key:
                self._color_combo.setCurrentIndex(i)
                break
        self._color_combo.currentIndexChanged.connect(self._on_color_changed)
        self._color_combo.hide()

        from PySide6.QtWidgets import QCheckBox

        self._bg_check = QCheckBox("Nền nhạt")
        self._bg_check.setChecked(
            str(self._settings.value("signatureBg", "1")) not in ("0", "false", "False")
        )
        self._bg_check.toggled.connect(self._on_bg_toggled)
        self._bg_check.hide()

        self._logo_check = QCheckBox("Logo")
        self._logo_check.setChecked(
            str(self._settings.value("signatureLogo", "0")) not in ("0", "false", "False")
        )
        self._logo_check.toggled.connect(self._on_logo_toggled)
        self._logo_check.hide()

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Thao tác:"))
        self._sign_settings_btn = QPushButton("Cài đặt ký")
        self._sign_settings_btn.setToolTip(
            "Chế độ ký · màu chữ · nền · logo · vị trí (lưu theo chứng thư)"
        )
        self._sign_settings_btn.clicked.connect(self._on_open_sign_settings)
        mode_row.addWidget(self._sign_settings_btn)
        self._retry_btn = QPushButton("Ký lại lỗi")
        self._retry_btn.clicked.connect(self._on_retry_failed)
        mode_row.addWidget(self._retry_btn)
        self._clear_btn = QPushButton("Xóa danh sách ký")
        self._clear_btn.setToolTip("Xóa toàn cả file trong danh sách (đã ký và chưa ký)")
        self._clear_btn.clicked.connect(self._on_clear_all)
        mode_row.addWidget(self._clear_btn)
        mode_row.addStretch(1)
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

    def _on_logo_toggled(self, checked: bool) -> None:
        self._settings.setValue("signatureLogo", "1" if checked else "0")
        self._save_active_profile()

    def _on_bg_toggled(self, checked: bool) -> None:
        self._settings.setValue("signatureBg", "1" if checked else "0")
        self._save_active_profile()

    def _on_color_changed(self, index: int) -> None:
        data = self._color_combo.itemData(index)
        if data:
            key, _rgb = data
            self._settings.setValue("signatureTextColor", key)
            self._save_active_profile()

    def _current_color_key(self) -> str:
        data = self._color_combo.currentData()
        return data[0] if data else "navy"

    def _select_mode(self, mode: str) -> None:
        for i in range(self._mode_combo.count()):
            if self._mode_combo.itemData(i) == mode:
                self._mode_combo.setCurrentIndex(i)
                return
        self._mode_combo.setCurrentIndex(1)

    def _load_cert_profile(self, fingerprint: str, company: str = "") -> None:
        """Load per-cert profile; fall back to app defaults if none."""
        self._active_fingerprint = fingerprint or None
        prof = self._cert_store.get(fingerprint) if fingerprint else None
        if prof is None:
            self._load_app_defaults()
            if company:
                self.statusBar().showMessage(
                    f"Chứng thư {company}: chưa có hồ sơ riêng — dùng cài đặt mặc định",
                    4000,
                )
            return
        self._select_mode(str(prof.signature_mode))
        for i in range(self._color_combo.count()):
            item = self._color_combo.itemData(i)
            if item and item[0] == prof.text_color_key:
                self._color_combo.setCurrentIndex(i)
                break
        self._bg_check.setChecked(prof.show_background)
        self._logo_check.setChecked(bool(prof.show_logo and prof.logo_path))
        if prof.logo_path:
            self._settings.setValue("signatureLogoPath", prof.logo_path)
        self._sig_page = int(prof.sig_page or 0)
        self._sig_origin = (
            (int(prof.sig_x), int(prof.sig_y))
            if prof.sig_x is not None and prof.sig_y is not None
            else None
        )
        self.statusBar().showMessage(f"Đã nạp hồ sơ chứng thư: {company or fingerprint[:16]}", 3000)

    def _load_app_defaults(self) -> None:
        """Apply last-used app-wide signature defaults (works without token)."""
        # Prevent widget toggles from re-saving half-loaded state
        blockers = []
        for w in (self._mode_combo, self._color_combo, self._bg_check, self._logo_check):
            try:
                blockers.append(w.blockSignals(True))
            except Exception:  # noqa: BLE001
                pass
        try:
            mode = str(self._settings.value("defaultSignatureMode", "visible"))
            self._select_mode(mode)
            color_key = str(self._settings.value("signatureTextColor", "navy"))
            for i in range(self._color_combo.count()):
                item = self._color_combo.itemData(i)
                if item and item[0] == color_key:
                    self._color_combo.setCurrentIndex(i)
                    break
            self._bg_check.setChecked(
                str(self._settings.value("signatureBg", "1")) not in ("0", "false", "False")
            )
            logo_path = str(self._settings.value("signatureLogoPath", "") or "")
            show_logo = str(self._settings.value("signatureLogo", "0")) not in (
                "0",
                "false",
                "False",
            )
            # No logo path → force off (never invent a default stamp logo)
            self._logo_check.setChecked(bool(show_logo and logo_path))
            self._sig_page = int(str(self._settings.value("sigPage", "0") or "0"))
            try:
                sx = self._settings.value("sigX", None)
                sy = self._settings.value("sigY", None)
                self._sig_origin = (
                    (int(str(sx)), int(str(sy)))
                    if sx is not None and sy is not None
                    else None
                )
            except (TypeError, ValueError):
                self._sig_origin = None
        finally:
            for w, prev in zip(
                (self._mode_combo, self._color_combo, self._bg_check, self._logo_check),
                blockers,
                strict=False,
            ):
                try:
                    w.blockSignals(prev)
                except Exception:  # noqa: BLE001
                    pass

    def _save_app_defaults(self) -> None:
        logo_path = str(self._settings.value("signatureLogoPath", "") or "")
        show_logo = self._logo_check.isChecked() and bool(logo_path)
        self._settings.setValue("defaultSignatureMode", self._mode_combo.currentData())
        self._settings.setValue("signatureTextColor", self._current_color_key())
        self._settings.setValue("signatureBg", "1" if self._bg_check.isChecked() else "0")
        self._settings.setValue("signatureLogo", "1" if show_logo else "0")
        self._settings.setValue("sigPage", str(self._sig_page))
        if self._sig_origin:
            self._settings.setValue("sigX", str(self._sig_origin[0]))
            self._settings.setValue("sigY", str(self._sig_origin[1]))
        else:
            self._settings.remove("sigX")
            self._settings.remove("sigY")

    def _save_active_profile(self) -> None:
        """Always persist app defaults; also write cert profile when a cert is active."""
        self._save_app_defaults()
        fp = self._active_fingerprint
        if not fp:
            return
        logo_path = str(self._settings.value("signatureLogoPath", "") or "")
        show_logo = self._logo_check.isChecked() and bool(logo_path)
        mode_key = self._mode_combo.currentData() or "visible"
        company = ""
        engine = self._token_signer or self._lab_signer
        if engine is not None and getattr(engine, "cert_info", None) is not None:
            company = common_name_from_subject(str(engine.cert_info.subject))
        prof = CertProfile(
            fingerprint=fp,
            company=company,
            text_color_key=self._current_color_key(),
            show_logo=show_logo,
            logo_path=logo_path if show_logo else "",
            show_background=self._bg_check.isChecked(),
            signature_mode=str(mode_key),
            sig_page=self._sig_page,
            sig_x=float(self._sig_origin[0]) if self._sig_origin else None,
            sig_y=float(self._sig_origin[1]) if self._sig_origin else None,
        )
        self._cert_store.upsert(prof)

    def _apply_engine_appearance(self, engine) -> None:  # noqa: ANN001
        engine.text_color = self._selected_text_color()
        engine.show_background = self._bg_enabled()
        engine.show_logo = self._logo_check.isChecked()
        engine.logo_path = self._custom_logo_path()
        if engine.show_logo and engine.logo_path is None:
            engine.show_logo = False
        engine.sig_origin = self._sig_origin
        engine.sig_page = self._sig_page

    def _make_profile(self, engine) -> SigningProfile:  # noqa: ANN001
        from golden_signing.signing.contracts import SignatureMode

        profile = pus_safe_profile(
            certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256
        )
        mode_key = self._mode_combo.currentData() or "visible"
        profile.mode = (
            SignatureMode.VISIBLE if mode_key == "visible" else SignatureMode.INVISIBLE
        )
        return profile

    def _run_batch(self, batch: BatchEngine, jobs: list) -> None:
        self._batch_engine = batch
        self._batch_paused = False
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
        # audit history
        fp = self._active_fingerprint or ""
        mode_key = str(self._mode_combo.currentData() or "visible")
        import contextlib

        for j in batch.jobs:
            with contextlib.suppress(Exception):
                self._history.record(
                    input_path=str(j.input_path),
                    output_path=str(j.output_path) if j.output_path else None,
                    status=j.state.value,
                    error_code=j.error_code,
                    message=j.message,
                    certificate=fp,
                    profile_mode=mode_key,
                )

        failed_msgs = [
            f"{j.input_path.name}: {j.message}" for j in result.jobs if j.error_code
        ]
        extra = ("\n\n" + "\n".join(failed_msgs[:5])) if failed_msgs else ""
        title = "Golden Signing"
        out_dir = batch._output_dir if hasattr(batch, "_output_dir") else ""  # noqa: SLF001
        if result.failed:
            QMessageBox.warning(
                self,
                title,
                f"Hoàn tất: {result.success} thành công · {result.failed} lỗi · "
                f"{result.cancelled} hủy\nThư mục: {out_dir}{extra}",
            )
        else:
            QMessageBox.information(
                self,
                title,
                f"Hoàn tất: {result.success} thành công · 0 lỗi\nThư mục: {out_dir}",
            )

    def _sample_pdf_for_position(self) -> Path | None:
        jobs = self._model.jobs()
        for j in jobs:
            if j.input_path.is_file():
                return Path(j.input_path)
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn PDF để xem trước", "", "PDF (*.pdf)")
        if files:
            return Path(files[0])
        return None

    def _on_pick_position(self) -> None:
        pdf = self._sample_pdf_for_position()
        if pdf is None:
            QMessageBox.information(self, "Golden Signing", "Cần ít nhất một PDF trong danh sách.")
            return
        from golden_signing.signing.appearance import estimate_stamp_box
        from golden_signing.ui.sig_position_dialog import SigPositionDialog

        text_w, text_h = 240, 80
        try:
            from golden_signing.signing.appearance import build_stamp_text

            sample_text = build_stamp_text(company="Preview", mst="0", serial="0")
            box = estimate_stamp_box(sample_text, with_logo=self._logo_check.isChecked())
            text_w, text_h = box[2] - box[0], box[3] - box[1]
        except Exception:  # noqa: BLE001
            pass
        dlg = SigPositionDialog(
            pdf,
            page=self._sig_page,
            origin=self._sig_origin,
            box_size=(text_w, text_h),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        pos = dlg.result_position()
        if not pos:
            return
        page, x, y = pos
        self._sig_page = page
        self._sig_origin = (x, y)
        self._save_active_profile()
        self.statusBar().showMessage(f"Vị trí chữ ký: trang {page + 1} ({x}, {y})", 4000)

    def _on_verify_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileNames(self, "Chọn PDF để xác minh", "", "PDF (*.pdf)")
        if not path:
            return
        from golden_signing.ui.verify_dialog import format_verify_report

        report = format_verify_report(Path(path[0]))
        QMessageBox.information(self, "Xác minh chữ ký", report)

    def _on_retry_failed(self) -> None:
        jobs = list(self._model.jobs())
        failed = [
            j
            for j in jobs
            if j.state.value
            in {
                "PREFLIGHT_FAILED",
                "SIGN_FAILED",
                "VERIFY_FAILED",
                "TOKEN_ERROR",
                "IO_ERROR",
                "FINALIZE_FAILED",
            }
        ]
        if not failed:
            QMessageBox.information(self, "Golden Signing", "Không có file lỗi để ký lại.")
            return
        engine = self._token_signer or self._lab_signer
        if engine is None:
            QMessageBox.information(self, "Golden Signing", "Hãy ký ít nhất một lần trước.")
            return
        from golden_signing.batch.state import JobState

        for j in failed:
            j.state = JobState.DISCOVERED
            j.error_code = None
            j.message = "queued for retry"
        self._reload_table()
        self._apply_engine_appearance(engine)
        profile = self._make_profile(engine)
        out_dir = self._resolve_output_dir(jobs)
        batch = BatchEngine(
            engine, profile, output_dir=out_dir, on_progress=self._on_batch_progress
        )
        batch.enqueue_jobs(failed)
        self._run_batch(batch, failed)

    def _custom_logo_path(self) -> Path | None:
        raw = str(self._settings.value("signatureLogoPath", "") or "")
        if raw and Path(raw).is_file():
            return Path(raw)
        return None

    def _selected_text_color(self):  # noqa: ANN201
        data = self._color_combo.currentData()
        if data:
            return data[1]
        return None

    def _bg_enabled(self) -> bool:
        return bool(self._bg_check.isChecked())

    def _on_choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file đã ký")
        if folder:
            self._out_edit.setText(folder)

    def _resolve_output_dir(self, jobs: list) -> Path:
        text = self._out_edit.text().strip()
        if text:
            return Path(text)
        default_dir = str(self._settings.value("defaultOutputDir", "") or "")
        if default_dir:
            return Path(default_dir)
        if jobs:
            return jobs[0].input_path.parent / "signed"
        return Path.cwd() / "signed"

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

    # --- nav ----------------------------------------------------------

    def _nav_profiles(self) -> None:
        from golden_signing.ui.profiles_dialog import ProfilesDialog

        dlg = ProfilesDialog(self._cert_store, self)
        dlg.exec()
        # If user deleted active profile, reset UI defaults
        if self._active_fingerprint and self._cert_store.get(self._active_fingerprint) is None:
            self._logo_check.setChecked(False)
            self.statusBar().showMessage("Hồ sơ chứng thư đang dùng đã bị xóa", 4000)

    def _on_open_sign_settings(self) -> None:
        from golden_signing.ui.sign_settings_dialog import SignSettingsDialog

        sample = None
        for j in self._model.jobs():
            if Path(j.input_path).is_file():
                sample = Path(j.input_path)
                break
        dlg = SignSettingsDialog(
            mode=str(self._mode_combo.currentData() or "visible"),
            color_key=self._current_color_key(),
            show_bg=self._bg_check.isChecked(),
            show_logo=self._logo_check.isChecked(),
            logo_path=str(self._settings.value("signatureLogoPath", "") or ""),
            sig_page=self._sig_page,
            sig_origin=self._sig_origin,
            sample_pdf=sample,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        r = dlg.values()
        self._select_mode(str(r["mode"]))
        for i in range(self._color_combo.count()):
            item = self._color_combo.itemData(i)
            if item and item[0] == r["color_key"]:
                self._color_combo.setCurrentIndex(i)
                break
        self._bg_check.setChecked(bool(r["show_bg"]))
        self._logo_check.setChecked(bool(r["show_logo"]))
        if r["logo_path"]:
            self._settings.setValue("signatureLogoPath", r["logo_path"])
        self._sig_page = int(r["sig_page"])
        self._sig_origin = r["sig_origin"]
        self._settings.setValue("signatureTextColor", r["color_key"])
        self._settings.setValue("signatureBg", "1" if r["show_bg"] else "0")
        self._settings.setValue("signatureLogo", "1" if r["show_logo"] else "0")
        self._save_active_profile()
        self.statusBar().showMessage("Đã lưu cài đặt ký", 3000)

    def _on_clear_all(self) -> None:
        if self._model.rowCount() == 0:
            return
        ret = QMessageBox.question(
            self,
            "Xóa danh sách ký",
            f"Xóa toàn bộ {self._model.rowCount()} file trong danh sách?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self._model.replace_jobs([])
        self._reload_table()
        self._update_summary()

    def _nav_history(self) -> None:
        from golden_signing.ui.history_dialog import HistoryDialog

        HistoryDialog(self._history, self).exec()

    def _nav_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        dlg.exec()
        self._load_app_defaults()

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
        signer.cert_info = chosen
        if getattr(chosen, "fingerprint_sha256", ""):
            signer.certificate_fingerprint_sha256 = chosen.fingerprint_sha256
        self._token_signer = signer
        cn = common_name_from_subject(chosen.subject)
        self._profile_label.setText(f"Profile: PUS Safe · {_ellipsis(cn, 32)}")
        self._token_note.setText(
            f"Đã kết nối: {_ellipsis(cn, 40)}\nToken: {chosen.token_label or 'USB'}"
        )
        self._load_cert_profile(
            getattr(chosen, "fingerprint_sha256", "") or "",
            company=cn,
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
            name_item = QTableWidgetItem(job.input_path.name)
            self._table.setItem(row, 0, name_item)
            status = QTableWidgetItem(job.state.value)
            if job.message:
                status.setToolTip(f"{job.state.value}: {job.message}")
            self._table.setItem(row, 1, status)
            self._table.setCellWidget(row, 2, self._make_action_widget(job))

    def _make_action_widget(self, job) -> QWidget:  # noqa: ANN001
        from PySide6.QtWidgets import QWidget

        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        def _btn(text: str, slot) -> QPushButton:  # noqa: ANN001
            b = QPushButton(text)
            b.setFixedHeight(24)
            b.setMinimumWidth(64)
            b.clicked.connect(lambda _=False, j=job: slot(j))
            return b

        open_btn = _btn("Mở", self._open_job_file)
        folder_btn = _btn("Thư mục", self._open_job_folder)
        del_btn = _btn("Xóa", self._delete_job_row)
        lay.addWidget(open_btn)
        lay.addWidget(folder_btn)
        lay.addWidget(del_btn)
        if job.error_code or job.message:
            detail = _btn("Chi tiết", self._show_job_error)
            lay.addWidget(detail)
        lay.addStretch(1)
        return wrap

    def _delete_job_row(self, job) -> None:  # noqa: ANN001
        jobs = [j for j in self._model.jobs() if j is not job]
        self._model.replace_jobs(jobs)
        self._reload_table()
        self._update_summary()

    def _show_job_error(self, job) -> None:  # noqa: ANN001
        from golden_signing.ui.job_error_dialog import JobErrorDialog

        JobErrorDialog(job, self).exec()

    def _open_job_file(self, job) -> None:  # noqa: ANN001
        target = None
        if job.output_path and Path(job.output_path).exists():
            target = Path(job.output_path)
        elif Path(job.input_path).is_file():
            target = Path(job.input_path)
        if target is None:
            QMessageBox.warning(self, "Golden Signing", "Không tìm thấy file.")
            return
        self._open_path(target)

    def _open_job_folder(self, job) -> None:  # noqa: ANN001
        if job.output_path and Path(job.output_path).exists():
            folder = Path(job.output_path).parent
        else:
            folder = Path(job.input_path).parent
        folder.mkdir(parents=True, exist_ok=True)
        self._open_path(folder)

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
                fp = getattr(engine, "certificate_fingerprint_sha256", "") or ""
                if fp and self._active_fingerprint != fp:
                    self._load_cert_profile(fp, company="Golden Signing Lab")

        profile = self._make_profile(engine)
        self._apply_engine_appearance(engine)
        self._save_active_profile()
        out_dir = self._resolve_output_dir(jobs)
        batch = BatchEngine(
            engine,
            profile,
            output_dir=out_dir,
            on_progress=self._on_batch_progress,
        )
        self._run_batch(batch, jobs)

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
