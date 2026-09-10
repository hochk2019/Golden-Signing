"""File/job table model for the main window list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from golden_signing.batch.state import JobState, SigningJob

__all__ = ["FileJobTableModel"]

_HEADERS = ("Tên file", "Trạng thái", "Hành động")


class FileJobTableModel(QAbstractTableModel):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self._jobs: list[SigningJob] = []

    def rowCount(self, parent: Any = None) -> int:  # noqa: N802, ANN401
        if parent is not None and hasattr(parent, "isValid") and parent.isValid():
            return 0
        return len(self._jobs)

    def columnCount(self, parent: Any = None) -> int:  # noqa: N802, ANN401
        if parent is not None and hasattr(parent, "isValid") and parent.isValid():
            return 0
        return len(_HEADERS)

    def data(self, index: Any, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: ANN401
        if index is None or not index.isValid():
            return None
        row = index.row()
        if not (0 <= row < len(self._jobs)):
            return None
        job = self._jobs[row]
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return job.input_path.name
            if index.column() == 1:
                state = job.state.value
                if job.error_code and job.message:
                    return f"{state}"
                return state
            return ""
        if role == Qt.ItemDataRole.ToolTipRole and index.column() == 1:
            if job.message:
                return f"{job.state.value}: {job.message}"
            return job.state.value
        return None

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(_HEADERS)
        ):
            return _HEADERS[section]
        return None

    def jobs(self) -> list[SigningJob]:
        return list(self._jobs)

    def add_paths(self, paths: list[Path]) -> None:
        existing = {j.input_path.resolve() for j in self._jobs}
        new_jobs: list[SigningJob] = []
        for p in paths:
            rp = Path(p).resolve()
            if rp in existing or not rp.is_file():
                continue
            if rp.suffix.lower() != ".pdf":
                continue
            new_jobs.append(SigningJob(input_path=rp))
            existing.add(rp)
        if not new_jobs:
            return
        start = len(self._jobs)
        self.beginInsertRows(QModelIndex(), start, start + len(new_jobs) - 1)
        self._jobs.extend(new_jobs)
        self.endInsertRows()

    def replace_jobs(self, jobs: list[SigningJob]) -> None:
        self.beginResetModel()
        self._jobs = list(jobs)
        self.endResetModel()

    def refresh_row(self, row: int) -> None:
        if 0 <= row < len(self._jobs):
            left = self.index(row, 0)
            right = self.index(row, len(_HEADERS) - 1)
            self.dataChanged.emit(left, right, [Qt.ItemDataRole.DisplayRole])

    def summary(self) -> tuple[int, int, int]:
        ok = sum(1 for j in self._jobs if j.state is JobState.SUCCESS)
        err = sum(
            1
            for j in self._jobs
            if j.is_terminal and j.state not in (JobState.SUCCESS, JobState.SKIPPED, JobState.CANCELLED)
        )
        return len(self._jobs), ok, err
