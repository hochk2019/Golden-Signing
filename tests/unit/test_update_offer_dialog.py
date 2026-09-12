"""Auto-update offer dialog smoke (offscreen)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextEdit  # noqa: E402

from golden_signing.ui.theme import apply_theme  # noqa: E402
from golden_signing.ui.update_offer_dialog import UpdateOfferDialog  # noqa: E402
from golden_signing.updater.check import DEFAULT_UPDATE_REPO, resolve_repo  # noqa: E402
from golden_signing.updater.github import UpdateInfo  # noqa: E402
from golden_signing.updater.version import parse_version  # noqa: E402


def test_default_repo_slug() -> None:
    assert DEFAULT_UPDATE_REPO == "hochk2019/Golden-Signing"
    assert resolve_repo("") == DEFAULT_UPDATE_REPO
    assert resolve_repo(None) == DEFAULT_UPDATE_REPO
    assert resolve_repo("other/repo") == "other/repo"


def test_offer_dialog_shows_notes() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    info = UpdateInfo(
        version=parse_version("v9.9.9"),
        tag="v9.9.9",
        html_url="https://github.com/hochk2019/Golden-Signing/releases/tag/v9.9.9",
        body="- Thêm nút X\n- Sửa lỗi PIN",
        zip_name="GoldenSigning-9.9.9-win64.zip",
        zip_url="https://example/z.zip",
        checksums={},
    )
    dlg = UpdateOfferDialog(info, "0.1.0a0")
    assert dlg.windowTitle() == "Có bản cập nhật mới"
    te = dlg.findChild(QTextEdit)
    assert te is not None
    assert "Thêm nút X" in te.toPlainText()
    assert dlg.did_update is False
    dlg.close()
