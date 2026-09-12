"""Manual update check dialog (Giới thiệu → Kiểm tra cập nhật)."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

__all__ = ["UpdateCheckDialog"]


class UpdateCheckDialog(QDialog):
    def __init__(
        self,
        settings: QSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cập nhật")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        self._status = QLabel("Nhấn “Kiểm tra” để dò bản mới trên GitHub Releases.")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._detail = QLabel("")
        self._detail.setObjectName("productSub")
        self._detail.setWordWrap(True)
        self._detail.setTextFormat(Qt.TextFormat.PlainText)
        self._detail.hide()
        root.addWidget(self._detail)

        actions = QHBoxLayout()
        self._check_btn = QPushButton("Kiểm tra")
        self._check_btn.clicked.connect(self._on_check)
        actions.addWidget(self._check_btn)
        self._open_btn = QPushButton("Mở trang Release")
        self._open_btn.clicked.connect(self._on_open_release)
        self._open_btn.hide()
        actions.addWidget(self._open_btn)
        self._stage_btn = QPushButton("Tải & chuẩn bị")
        self._stage_btn.setToolTip(
            "Tải zip, kiểm SHA256, giải nén vào thư mục updates. "
            "Thay app onedir cần tiến trình ngoài khi app đã đóng."
        )
        self._stage_btn.clicked.connect(self._on_stage)
        self._stage_btn.hide()
        actions.addWidget(self._stage_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

        self._release_url: str | None = None
        self._zip_url: str | None = None
        self._zip_name: str | None = None
        self._sha256: str | None = None
        self._tag: str | None = None

    def _repo(self) -> str:
        return str(self._settings.value("update/repo", "") or "").strip()

    def _on_check(self) -> None:
        from golden_signing.updater.check import check_for_update

        repo = self._repo()
        self._check_btn.setEnabled(False)
        self._status.setText("Đang kiểm tra GitHub…")
        self._detail.hide()
        self._open_btn.hide()
        self._stage_btn.hide()
        try:
            result = check_for_update(repo)
        finally:
            self._check_btn.setEnabled(True)

        if not result.ok:
            self._status.setText(f"Không kiểm tra được: {result.error}")
            return
        assert result.info is not None
        info = result.info
        self._release_url = info.html_url or None
        self._zip_url = info.zip_url
        self._zip_name = info.zip_name
        self._sha256 = info.zip_sha256()
        self._tag = info.tag
        self._open_btn.setVisible(bool(self._release_url))

        if not result.newer:
            self._status.setText(f"Đã là bản mới nhất (local {result.local.raw}, GitHub {info.tag}).")
            return

        self._status.setText(f"Có bản mới: {info.tag} (bạn đang dùng {result.local.raw}).")
        if info.zip_name:
            self._detail.setText(f"Asset: {info.zip_name}")
            self._detail.show()
            self._stage_btn.setVisible(True)
        else:
            self._detail.setText("Release không có zip Windows — dùng “Mở trang Release” để tải tay.")
            self._detail.show()

    def _on_open_release(self) -> None:
        if not self._release_url:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self._release_url))

    def _on_stage(self) -> None:
        from golden_signing.updater.apply import UpdateApplyError, stage_update
        from golden_signing.updater.check import check_for_update

        if not self._zip_url or not self._tag:
            return
        expected = self._sha256 or ""
        if not expected:
            # try refresh checksums
            result = check_for_update(self._repo())
            if result.ok and result.info:
                expected = result.info.zip_sha256() or ""
        self._stage_btn.setEnabled(False)
        self._status.setText("Đang tải và kiểm SHA256…")
        try:
            # Dev/source: only stage under updates/, do not replace running tree.
            stage_update(
                zip_url=self._zip_url,
                expected_sha256=expected,
                version_tag=self._tag,
                app_dir=None,
            )
        except UpdateApplyError as exc:
            self._status.setText(f"Lỗi: {exc}")
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"Lỗi: {exc}")
        else:
            from golden_signing.updater.apply import default_update_dir

            folder = default_update_dir()
            self._status.setText(
                f"Đã tải & kiểm hash OK.\nThư mục: {folder}\n"
                "Chạy bản onedir: thay thư mục cài rồi mở lại app."
            )
        finally:
            self._stage_btn.setEnabled(True)
