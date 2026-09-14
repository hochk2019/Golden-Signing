"""Offer dialog: new version found → notes → download with progress."""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from golden_signing.updater.check import CheckResult
from golden_signing.updater.github import UpdateInfo

__all__ = ["StageWorker", "UpdateCheckThread", "UpdateOfferDialog"]


def _fmt_mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


class UpdateCheckThread(QThread):
    result = Signal(object)  # CheckResult

    def __init__(self, repo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo

    def run(self) -> None:
        from golden_signing.updater.check import check_for_update

        self.result.emit(check_for_update(self._repo))


class StageWorker(QThread):
    """Download + SHA256 verify + extract on a background thread."""

    progress = Signal(int, int)  # done, total (total may be 0)
    finished_ok = Signal(object)  # ApplyResult
    failed = Signal(str)

    def __init__(
        self,
        *,
        zip_url: str,
        expected_sha256: str,
        version_tag: str,
        app_dir: Path | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._zip_url = zip_url
        self._sha = expected_sha256
        self._tag = version_tag
        self._app_dir = app_dir

    def run(self) -> None:
        try:
            from golden_signing.updater.apply import stage_update

            def _cb(done: int, total: int) -> None:
                self.progress.emit(done, total)

            result = stage_update(
                zip_url=self._zip_url,
                expected_sha256=self._sha,
                version_tag=self._tag,
                app_dir=self._app_dir,
                on_download_progress=_cb,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


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
        self.setMinimumSize(480, 400)
        self._info = info
        self._local_version = local_version
        self._did_update = False
        self._worker: StageWorker | None = None

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
        plain = html.unescape(body)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(plain)
        view.setMinimumHeight(160)
        wrap = QScrollArea()
        wrap.setWidgetResizable(True)
        wrap.setWidget(view)
        root.addWidget(wrap, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.hide()
        root.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setObjectName("productSub")
        self._status.setWordWrap(True)
        self._status.hide()
        root.addWidget(self._status)

        actions = QHBoxLayout()
        self._later_btn = QPushButton("Để sau")
        self._later_btn.clicked.connect(self._on_later)
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

    @property
    def did_update(self) -> bool:
        return self._did_update

    def _set_busy(self, busy: bool) -> None:
        self._update_btn.setEnabled(not busy)
        self._later_btn.setEnabled(not busy)

    def _open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(self._info.html_url))

    def _on_later(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.reject()

    def _on_update(self) -> None:
        info = self._info
        if not info.zip_url:
            self._status.setText("Release không có zip để tải — dùng “Mở GitHub”.")
            self._status.show()
            return
        from golden_signing.updater.runtime import app_install_dir, is_frozen

        install_dir = app_install_dir()
        self._set_busy(True)
        self._progress.setRange(0, 0)  # indeterminate until Content-Length known
        self._progress.show()
        self._status.setText("Đang tải bản cập nhật…")
        self._status.show()

        self._worker = StageWorker(
            zip_url=info.zip_url,
            expected_sha256=info.zip_sha256() or "",
            version_tag=info.tag,
            app_dir=install_dir if is_frozen() else None,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_staged)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._progress.setRange(0, 100)
            pct = min(100, int(done * 100 / max(total, 1)))
            self._progress.setValue(pct)
            self._status.setText(
                f"Đang tải… {_fmt_mb(done)} / {_fmt_mb(total)}"
            )
        else:
            self._progress.setRange(0, 0)
            self._status.setText(f"Đang tải… {_fmt_mb(done)}")

    def _on_staged(self, result: object) -> None:
        from golden_signing.updater.apply import apply_staged_swap
        from golden_signing.updater.runtime import is_frozen, relaunch_app

        extract_dir = getattr(result, "extract_dir", None)
        zip_path = getattr(result, "zip_path", None)
        install_dir = app_install_dir_frozen()

        if is_frozen() and install_dir is not None and extract_dir is not None:
            self._status.setText("Đang cài bản mới…")
            self._progress.setRange(0, 0)
            try:
                apply_staged_swap(
                    staged_dir=Path(extract_dir),
                    app_dir=install_dir,
                    update_root=Path(zip_path).parent if zip_path else install_dir.parent,
                )
            except Exception as exc:  # noqa: BLE001
                self._on_fail(str(exc))
                return
            self._did_update = True
            self.accept()
            relaunch_app()
            return

        folder = Path(zip_path).parent if zip_path else None
        self._progress.hide()
        self._status.setText(
            f"Đã tải & kiểm hash OK ({self._info.tag}).\n"
            f"Thư mục: {folder}\n"
            "Chạy bản cài đặt (EXE) để tự thay và mở lại app."
        )
        self._set_busy(True)  # keep update disabled after success
        self._later_btn.setEnabled(True)
        self._later_btn.setText("Đóng")

    def _on_fail(self, message: str) -> None:
        self._progress.hide()
        self._status.setText(f"Cập nhật thất bại: {message}")
        self._set_busy(False)


def app_install_dir_frozen() -> Path | None:
    from golden_signing.updater.runtime import app_install_dir, is_frozen

    return app_install_dir() if is_frozen() else None


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
