"""Golden Sign main window — token-aware Phase 5 UI."""

from __future__ import annotations

import contextlib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
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
    from golden_signing.storage.app_paths import brand_mark_path

    return brand_mark_path()


def _ellipsis(text: str, n: int) -> str:
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[: n - 1] + "…"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golden Sign — Sản phẩm của Golden Logistics")
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
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
        self._compress_sign_btn.setEnabled(False)
        self._compress_only_btn.setEnabled(False)
        self._token_note.setText("Đang quét USB token…")
        from PySide6.QtCore import QTimer

        if str(self._settings.value("autoScanToken", "1")) not in ("0", "false", "False"):
            QTimer.singleShot(400, self._refresh_token_label)
        else:
            self._token_note.setText("Tự quét token đã tắt (Cài đặt).")
        self._load_app_defaults()
        self._sync_output_dir_from_settings()
        self._update_thread = None
        if str(self._settings.value("autoCheckUpdate", "1")) not in ("0", "false", "False"):
            QTimer.singleShot(1800, self._auto_check_update)

    def _build_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(220)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(8)

        mark = QLabel()
        mark.setObjectName("brandMark")
        mark.setFixedWidth(40)
        mark_path = _brand_mark_path()
        if mark_path.is_file():
            from PySide6.QtGui import QPixmap

            pix = QPixmap(str(mark_path)).scaled(
                40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            mark.setPixmap(pix)
        mark.setFixedHeight(40)
        lay.addWidget(mark)

        title = QLabel("Golden Sign")
        title.setObjectName("productTitle")
        sub = QLabel("Ký số PDF")
        sub.setObjectName("productSub")
        designer = QLabel("Designer: Hoc HK")
        designer.setObjectName("productMeta")
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addWidget(designer)
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

        drop = QLabel("Kéo thả PDF, Word hoặc Excel vào đây")
        drop.setObjectName("dropHint")
        drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(drop)
        subdrop = QLabel("PDF • DOC • DOCX • XLS • XLSX")
        subdrop.setObjectName("productSub")
        subdrop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(subdrop)

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

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Tên file", "Dung lượng", "Trạng thái", "Hành động"]
        )
        tbl_header = self._table.horizontalHeader()
        if tbl_header is not None:
            tbl_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            tbl_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            tbl_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            tbl_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            tbl_header.setStretchLastSection(False)
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(3, 292)
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
        self._compress_settings_btn = QPushButton("Cài đặt nén")
        self._compress_settings_btn.clicked.connect(self._on_compression_settings)
        mode_row.addWidget(self._compress_settings_btn)
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

        def _cta(text: str, tip: str) -> QPushButton:
            b = QPushButton(text)
            b.setObjectName("primaryCta")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(40)
            b.setMinimumWidth(110)
            if tip:
                b.setToolTip(tip)
            return b

        self._sign_btn = _cta("KÝ SỐ", "")
        self._sign_btn.clicked.connect(lambda: self._on_sign(compress=False))
        footer.addWidget(self._sign_btn)
        self._compress_only_btn = _cta(
            "CHỈ NÉN", "Chỉ nén PDF/Office→PDF, không ký số"
        )
        self._compress_only_btn.clicked.connect(self._on_compress_only)
        footer.addWidget(self._compress_only_btn)
        self._compress_sign_btn = _cta(
            "NÉN VÀ KÝ SỐ", "Nén PDF (theo Cài đặt nén) rồi ký số"
        )
        self._compress_sign_btn.clicked.connect(lambda: self._on_sign(compress=True))
        footer.addWidget(self._compress_sign_btn)
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
            with contextlib.suppress(Exception):
                blockers.append(w.blockSignals(True))
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
                with contextlib.suppress(Exception):
                    w.blockSignals(prev)

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
        try:
            engine.background_opacity = float(
                str(self._settings.value("signatureBgOpacity", "0.55") or "0.55")
            )
        except (TypeError, ValueError):
            engine.background_opacity = 0.55
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
        self._compress_sign_btn.setEnabled(False)
        self._compress_only_btn.setEnabled(False)
        try:
            result = batch.run()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Golden Sign", f"Lỗi khi xử lý:\n{exc}")
            self._update_summary()
            return
        finally:
            self._update_summary()

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
        title = "Golden Sign"
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
        pdf = self._sample_pdf_for_position()  # None → blank A4
        from golden_signing.signing.appearance import build_stamp_text, estimate_stamp_box
        from golden_signing.ui.sig_position_dialog import SigPositionDialog

        sample_text = build_stamp_text(company="Preview", mst="0", serial="0")
        box = estimate_stamp_box(sample_text, with_logo=self._logo_check.isChecked())
        dlg = SigPositionDialog(
            pdf,
            page=self._sig_page,
            origin=self._sig_origin,
            box_size=(box[2] - box[0], box[3] - box[1]),
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
            QMessageBox.information(self, "Golden Sign", "Không có file lỗi để ký lại.")
            return
        engine = self._token_signer or self._lab_signer
        if engine is None:
            QMessageBox.information(self, "Golden Sign", "Hãy ký ít nhất một lần trước.")
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
            engine, profile, output_dir=out_dir, on_progress=self._on_batch_progress,
            on_job_state=self._on_job_state,
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

    def _sync_output_dir_from_settings(self) -> None:
        """Show persisted defaultOutputDir in the main output field."""
        default_dir = str(self._settings.value("defaultOutputDir", "") or "")
        self._out_edit.setText(default_dir)

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
            QMessageBox.warning(self, "Golden Sign", f"Không mở được:\n{exc}")

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
            background_opacity=float(
                str(self._settings.value("signatureBgOpacity", "0.55") or "0.55")
            ),
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
        self._settings.setValue(
            "signatureBgOpacity", str(float(r.get("background_opacity", 0.55)))
        )
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
        was_scan = str(self._settings.value("autoScanToken", "1")) not in (
            "0",
            "false",
            "False",
        )
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._load_app_defaults()
        self._sync_output_dir_from_settings()
        now_scan = str(self._settings.value("autoScanToken", "1")) not in (
            "0",
            "false",
            "False",
        )
        if now_scan and not was_scan:
            self._refresh_token_label()
        elif not now_scan and was_scan:
            self._token_note.setText("Tự quét token đã tắt (Cài đặt).")
        self.statusBar().showMessage("Đã lưu cài đặt", 2500)

    def _nav_about(self) -> None:
        from golden_signing import __version__
        from golden_signing.ui.theme import apply_window_icon
        from golden_signing.ui.update_dialog import UpdateCheckDialog

        dlg = QDialog(self)
        apply_window_icon(dlg)
        dlg.setWindowTitle("Giới thiệu")
        dlg.setModal(True)
        dlg.setMinimumWidth(440)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)
        info = QLabel(
            "Golden Sign\nPDF Digital Signature Utility\n"
            "Developer: HOC HK\nhochk2019@gmail.com · 0868.333.606\n"
            f"Phiên bản {__version__}\n\n"
            "Đây là ứng dụng phi lợi nhuận, không nhằm mục đích thương mại, "
            "người dùng tự chịu mọi trách nhiệm khi sử dụng ứng dụng này để ký số file PDF.\n\n"
            "Liên hệ để được tư vấn thủ tục hải quan miễn phí — "
            "Làm thủ tục Hải quan và dịch vụ vận chuyển toàn quốc."
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        check_btn = QPushButton("Kiểm tra cập nhật")
        check_btn.clicked.connect(lambda: UpdateCheckDialog(self._settings, self).exec())
        row.addWidget(check_btn)
        row.addStretch(1)
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(dlg.accept)
        row.addWidget(close_btn)
        lay.addLayout(row)
        dlg.exec()

    def _auto_check_update(self) -> None:
        """Background check on launch; offer dialog only when a newer release exists."""
        from golden_signing.ui.update_offer_dialog import UpdateCheckThread
        from golden_signing.updater.check import resolve_repo

        if self._update_thread is not None and self._update_thread.isRunning():
            return
        repo = resolve_repo(str(self._settings.value("update/repo", "") or ""))
        self._update_thread = UpdateCheckThread(repo, self)
        self._update_thread.result.connect(self._on_auto_update_result)
        self._update_thread.start()

    def _on_auto_update_result(self, result: object) -> None:
        from golden_signing.ui.update_offer_dialog import offer_if_newer

        ok = bool(getattr(result, "ok", False))
        newer = bool(getattr(result, "newer", False))
        if not ok or not newer:
            return
        did = offer_if_newer(result, self)  # type: ignore[arg-type]
        if did:
            # Staged swap + relaunch already started — exit this process.
            self.close()
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()

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
        from golden_signing.ui.cert_label import common_name_from_subject
        from golden_signing.ui.token_dialogs import CertPickerDialog, PinDialog

        dlls = discover_pkcs11_libraries()
        if not dlls:
            QMessageBox.warning(
                self,
                "Token",
                "Không tìm thấy thư viện PKCS#11 / USB token.\n"
                "Cắm token và thử lại, hoặc dùng Quét lại token.",
            )
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
        company = common_name_from_subject(getattr(chosen, "subject", "") or "")
        pin_dlg = PinDialog(company=company, parent=self)
        if pin_dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        pin = pin_dlg.pin()
        if not pin:
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
        exts = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
        for p in paths:
            if p.is_dir():
                for e in exts:
                    files.extend(sorted(p.glob(f"*{e}")))
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
        has_detail = False
        for row, job in enumerate(jobs):
            name_item = QTableWidgetItem(job.input_path.name)
            self._table.setItem(row, 0, name_item)
            try:
                sz = job.input_path.stat().st_size
            except OSError:
                sz = 0
            src_sz = job.source_size or sz
            parts = []
            if src_sz >= 1024 * 1024:
                parts.append(f"{src_sz / (1024 * 1024):.1f} MB")
            else:
                parts.append(f"{max(src_sz, 0) // 1024} KB")
            if job.compressed_size is not None and job.compressed_size > 0:
                cs = job.compressed_size
                cs_t = (
                    f"{cs / (1024 * 1024):.1f} MB"
                    if cs >= 1024 * 1024
                    else f"{cs // 1024} KB"
                )
                parts.append(cs_t)
            size_text = " → ".join(parts)
            self._table.setItem(row, 1, QTableWidgetItem(size_text))
            status = QTableWidgetItem(job.state.value)
            if job.message:
                status.setToolTip(f"{job.state.value}: {job.message}")
            self._table.setItem(row, 2, status)
            self._table.setCellWidget(row, 3, self._make_action_widget(job))
            if job.error_code or job.message:
                has_detail = True
        self._table.setColumnWidth(3, 384 if has_detail else 292)

    def _make_action_widget(self, job) -> QWidget:  # noqa: ANN001
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QWidget

        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        # Vertical margins 0 + AlignVCenter: 24px button sits mid 36px row
        # so the bottom border is fully visible (matches status text height).
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)
        lay.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        def _btn(text: str, slot) -> QPushButton:  # noqa: ANN001
            b = QPushButton(text)
            b.setObjectName("tableActionBtn")
            b.setFixedSize(88, 24)
            b.clicked.connect(lambda _=False, j=job: slot(j))
            return b

        open_btn = _btn("Mở file", self._open_job_file)
        folder_btn = _btn("Mở Thư mục", self._open_job_folder)
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
            QMessageBox.warning(self, "Golden Sign", "Không tìm thấy file.")
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
        enable = total > 0
        self._sign_btn.setEnabled(enable)
        self._compress_sign_btn.setEnabled(enable)
        self._compress_only_btn.setEnabled(enable)

    def _on_compress_only(self) -> None:
        jobs = [j for j in self._model.jobs() if not j.is_terminal]
        if not jobs:
            QMessageBox.information(self, "Golden Sign", "Không có file chờ xử lý.")
            return
        from golden_signing.signing.pdf_signer import TestCertPdfSigner

        # Dummy engine — compress_only path never calls sign()
        engine = self._lab_signer or TestCertPdfSigner()
        self._lab_signer = engine
        profile = self._make_profile(engine)
        out_dir = self._resolve_output_dir(jobs)
        batch = BatchEngine(
            engine,
            profile,
            output_dir=out_dir,
            on_progress=self._on_batch_progress,
            compress_only=True,
            compression_profile=self._load_compression_profile(),
            on_job_state=self._on_job_state,
        )
        self._run_batch(batch, jobs)

    def _on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn file",
            "",
            "Tài liệu (*.pdf *.doc *.docx *.xls *.xlsx);;PDF (*.pdf)",
        )
        self.add_paths([Path(f) for f in files])

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder:
            self.add_paths([Path(folder)])

    # --- sign ---------------------------------------------------------

    def _load_compression_profile(self):
        import json

        from golden_signing.compress.engine import CompressionProfile, default_profile

        raw = str(self._settings.value("compressionProfile", "") or "")
        if not raw:
            return default_profile()
        try:
            data = json.loads(raw)
            return CompressionProfile(**data)
        except Exception:  # noqa: BLE001
            return default_profile()

    def _on_compression_settings(self) -> None:
        import json

        from golden_signing.ui.compression_dialog import CompressionSettingsDialog

        dlg = CompressionSettingsDialog(self._load_compression_profile(), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        prof = dlg.profile()
        from dataclasses import asdict

        self._settings.setValue("compressionProfile", json.dumps(asdict(prof)))
        self.statusBar().showMessage(f"Đã lưu cài đặt nén: {prof.name}", 3000)

    def _on_sign(self, *, compress: bool = False) -> None:
        jobs = [j for j in self._model.jobs() if not j.is_terminal]
        if not jobs:
            QMessageBox.information(self, "Golden Sign", "Không có file chờ ký.")
            return

        engine = self._token_signer
        if engine is None:
            engine = self._ensure_token_engine()
            if engine is None:
                return

        profile = self._make_profile(engine)
        self._apply_engine_appearance(engine)
        self._save_active_profile()
        out_dir = self._resolve_output_dir(jobs)
        batch = BatchEngine(
            engine,
            profile,
            output_dir=out_dir,
            on_progress=self._on_batch_progress,
            compress=compress,
            compression_profile=self._load_compression_profile() if compress else None,
            on_job_state=self._on_job_state,
        )
        self._run_batch(batch, jobs)

    def _on_job_state(self, job: object) -> None:
        """Live step label while a file is converting/compressing/signing."""
        try:
            name = Path(job.input_path).name  # type: ignore[attr-defined]
            state = str(job.state.value)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return
        label = {
            "CONVERTING": "đang chuyển PDF",
            "COMPRESSING": "đang nén",
            "SIGNING": "đang ký",
            "VERIFYING": "đang xác minh",
        }.get(state, state)
        self._summary.setText(f"{name} · {label}")
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

    def _on_batch_progress(self, done: int, total: int, job: object) -> None:
        name = ""
        state = ""
        try:
            name = Path(job.input_path).name  # type: ignore[attr-defined]
            state = str(job.state.value)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        if name:
            self._summary.setText(f"Đang xử lý {done}/{total} · {name} · {state}")
        else:
            self._summary.setText(f"Đang xử lý {done}/{total}…")
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()


def run_app() -> int:
    import sys

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from golden_signing.storage.app_paths import app_icon_path

    app = QApplication(sys.argv)
    app.setApplicationName("Golden Sign")
    app.setOrganizationName("HOCHK")
    icon_path = app_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    apply_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()
