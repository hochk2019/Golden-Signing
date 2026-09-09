"""Golden Signing main window — Phase 5 minimal usable UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from golden_signing.ui.file_table import FileJobTableModel
from golden_signing.ui.theme import apply_theme

__all__ = ["MainWindow"]


def _brand_mark_path() -> Path:
    # repo-relative: src/golden_signing/ui → repo root assets
    here = Path(__file__).resolve()
    root = here.parents[3]
    return root / "assets" / "branding" / "golden-mark.png"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golden Signing — Ký số PDF")
        self.resize(960, 640)
        self.setAcceptDrops(True)

        self._model = FileJobTableModel(self)
        self._engine: TestCertPdfSigner | None = None

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_rail())
        root.addWidget(self._build_workspace(), stretch=1)
        self.setCentralWidget(central)
        self._update_summary()
        self._sign_btn.setEnabled(False)

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
        lay.addSpacing(24)

        for label in ("Ký tài liệu", "Hồ sơ ký", "Cài đặt", "Giới thiệu"):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(btn)
        lay.addStretch(1)
        note = QLabel("Lab certificate\nChưa kết nối USB token")
        note.setObjectName("productSub")
        note.setWordWrap(True)
        lay.addWidget(note)
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
        self._drop = drop
        lay.addWidget(drop)

        actions = QHBoxLayout()
        self._add_btn = QPushButton("Thêm PDF")
        self._add_dir_btn = QPushButton("Thêm thư mục")
        self._add_btn.clicked.connect(self._on_add_files)
        self._add_dir_btn.clicked.connect(self._on_add_folder)
        actions.addWidget(self._add_btn)
        actions.addWidget(self._add_dir_btn)
        actions.addStretch(1)
        self._profile_label = QLabel("Profile: PUS Safe · Chứng thư: lab (test cert)")
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

    # --- drag/drop ----------------------------------------------------

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

    def _on_sign(self) -> None:
        jobs = [j for j in self._model.jobs() if not j.is_terminal]
        if not jobs:
            QMessageBox.information(self, "Golden Signing", "Không có file chờ ký.")
            return
        if self._engine is None:
            self._engine = TestCertPdfSigner()
        profile = pus_safe_profile(
            certificate_fingerprint_sha256=self._engine.certificate_fingerprint_sha256
        )
        out_dir = jobs[0].input_path.parent / "signed"
        batch = BatchEngine(
            self._engine,
            profile,
            output_dir=out_dir,
            on_progress=self._on_batch_progress,
        )
        batch.enqueue_jobs(jobs)
        self._sign_btn.setEnabled(False)
        try:
            result = batch.run()
        finally:
            self._sign_btn.setEnabled(True)
        self._model.replace_jobs(list(batch.jobs))
        self._reload_table()
        self._update_summary()
        QMessageBox.information(
            self,
            "Golden Signing",
            f"Hoàn tất: {result.success} thành công · {result.failed} lỗi · {result.cancelled} hủy\n"
            f"Thư mục: {out_dir}",
        )

    def _on_batch_progress(self, done: int, total: int, job: object) -> None:
        self._summary.setText(f"Đang ký {done}/{total}…")
        # keep UI responsive
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
