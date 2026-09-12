"""Offer dialog: new version found → show notes → user chooses update or skip."""

from __future__ import annotations

import html

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from golden_signing.updater.check import CheckResult
from golden_signing.updater.github import UpdateInfo

__all__ = ["UpdateCheckThread", "UpdateOfferDialog"]


class UpdateCheckThread(QThread):
    result = Signal(object)  # CheckResult

    def __init__(self, repo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo

    def run(self) -> None:
        from golden_signing.updater.check import check_for_update

        self.result.emit(check_for_update(self._repo))


class UpdateOfferDialog(QDialog):
    """Shown when a newer GitHub release exists."""

    def __init__(
        self,
        info: UpdateInfo,
        local_version: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from golden_signing.ui.theme import apply_window_icon

        apply_window_icon(self)
        self.setWindowTitle("Có bản cập nhật mới")
        self.setModal(True)
        self.setMinimumSize(480, 360)
        self._info = info
        self._local_version = local_version
        self._did_update = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        head = QLabel(
            f"Golden Sign {info.tag} đã có sẵn.\n"
            f"Bạn đang dùng: {local_version}"
        )
        head.setWordWrap(True)
        root.addWidget(head)

        notes_label = QLabel("Tính năng / ghi chú release:")
        root.addWidget(notes_label)

        body = (info.body or "").strip() or "(Release không có mô tả)"
        # Show plain text; strip simple HTML tags if GitHub body is HTML-ish
        plain = html.unescape(body)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(plain)
        view.setMinimumHeight(180)
        wrap = QScrollArea()
        wrap.setWidgetResizable(True)
        wrap.setWidget(view)
        root.addWidget(wrap, stretch=1)

        actions = QHBoxLayout()
        self._later_btn = QPushButton("Để sau")
        self._later_btn.clicked.connect(self.reject)
        actions.addWidget(self._later_btn)
        actions.addStretch(1)
        if info.html_url:
            open_btn = QPushButton("Mở GitHub")
            open_btn.clicked.connect(self._open_github)
            actions.addWidget(open_btn)
        self._update_btn = QPushButton("Cập nhật ngay")
        self._update_btn.setDefault(True)
        self._update_btn.clicked.connect(self._on_update)
        actions.addWidget(self._update_btn)
        root.addLayout(actions)

        self._status = QLabel("")
        self._status.setObjectName("productSub")
        self._status.setWordWrap(True)
        self._status.hide()
        root.addWidget(self._status)

    @property
    def did_update(self) -> bool:
        return self._did_update

    def _open_github(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self._info.html_url))

    def _on_update(self) -> None:
        from golden_signing.updater.apply import (
            UpdateApplyError,
            apply_staged_swap,
            stage_update,
        )
        from golden_signing.updater.runtime import app_install_dir, is_frozen, relaunch_app

        info = self._info
        if not info.zip_url:
            self._status.setText("Release không có zip để tải — dùng “Mở GitHub”.")
            self._status.show()
            return
        expected = info.zip_sha256() or ""
        self._update_btn.setEnabled(False)
        self._later_btn.setEnabled(False)
        self._status.setText("Đang tải và kiểm SHA256…")
        self._status.show()
        try:
            install_dir = app_install_dir()
            result = stage_update(
                zip_url=info.zip_url,
                expected_sha256=expected,
                version_tag=info.tag,
                app_dir=install_dir if is_frozen() else None,
            )
            if is_frozen() and install_dir is not None:
                self._status.setText("Đang cài bản mới và khởi động lại…")
                apply_staged_swap(
                    staged_dir=result.extract_dir,
                    app_dir=install_dir,
                    update_root=result.zip_path.parent,
                )
                self._did_update = True
                self.accept()
                relaunch_app()
                # Caller quits QApplication after dialog closes
                return
            # Source/dev run: package is staged; cannot replace live tree safely.
            folder = result.zip_path.parent
            self._status.setText(
                f"Đã tải & kiểm hash OK ({info.tag}).\n"
                f"Thư mục: {folder}\n"
                "Chạy bản cài đặt (EXE) để tự thay và mở lại app."
            )
            self._update_btn.setEnabled(True)
            self._later_btn.setEnabled(True)
            self._later_btn.setText("Đóng")
        except UpdateApplyError as exc:
            self._status.setText(f"Cập nhật thất bại: {exc}")
            self._update_btn.setEnabled(True)
            self._later_btn.setEnabled(True)
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"Lỗi: {exc}")
            self._update_btn.setEnabled(True)
            self._later_btn.setEnabled(True)


def offer_if_newer(
    result: CheckResult,
    parent: QWidget | None = None,
) -> bool:
    """Show offer dialog when result.ok and newer. True if user completed update."""
    if not result.ok or not result.newer or result.info is None:
        return False
    dlg = UpdateOfferDialog(result.info, result.local.raw, parent)
    dlg.exec()
    return dlg.did_update
