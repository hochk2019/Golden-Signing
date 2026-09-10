"""Watch folder — add new PDFs automatically (debounced)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

__all__ = ["WatchFolder"]


class WatchFolder(QObject):
    """Poll a folder for new .pdf files; debounce until size stable."""

    def __init__(
        self,
        folder: Path,
        on_new_files: Callable[[list[Path]], None],
        *,
        interval_ms: int = 2500,
        stable_checks: int = 2,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.folder = Path(folder)
        self._on_new = on_new_files
        self._stable = stable_checks
        self._seen: dict[str, tuple[int, int]] = {}  # name -> (size, stable_count)
        self._known: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        # seed existing
        for p in self.folder.glob("*.pdf"):
            self._known.add(p.name)
            self._seen[p.name] = (p.stat().st_size, self._stable)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        try:
            files = list(self.folder.glob("*.pdf"))
        except OSError:
            return
        ready: list[Path] = []
        current_names = {p.name for p in files}
        for name in list(self._seen):
            if name not in current_names:
                self._seen.pop(name, None)
                self._known.discard(name)
        for p in files:
            if p.name in self._known:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            prev = self._seen.get(p.name)
            if prev is None:
                self._seen[p.name] = (size, 1)
                continue
            if size == prev[0]:
                count = prev[1] + 1
                self._seen[p.name] = (size, count)
                if count >= self._stable:
                    self._known.add(p.name)
                    ready.append(p)
            else:
                self._seen[p.name] = (size, 1)
        if ready:
            self._on_new(ready)
