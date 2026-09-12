"""SQLite signing history (audit log). Never stores PIN or private keys."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

__all__ = ["HistoryRecord", "SigningHistory", "default_history_path"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signing_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  input_path TEXT NOT NULL,
  output_path TEXT,
  status TEXT NOT NULL,
  error_code TEXT,
  message TEXT,
  certificate TEXT,
  profile_mode TEXT
);
CREATE INDEX IF NOT EXISTS idx_hist_ts ON signing_history(ts DESC);
"""


def default_history_path() -> Path:
    from golden_signing.storage.app_paths import data_dir

    return data_dir() / "history.db"


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    id: int
    ts: float
    input_path: str
    output_path: str | None
    status: str
    error_code: str | None
    message: str
    certificate: str | None
    profile_mode: str | None


class SigningHistory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_history_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(
        self,
        *,
        input_path: str,
        output_path: str | None,
        status: str,
        error_code: str | None = None,
        message: str = "",
        certificate: str | None = None,
        profile_mode: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO signing_history "
            "(ts, input_path, output_path, status, error_code, message, certificate, profile_mode) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                time.time(),
                input_path,
                output_path,
                status,
                error_code,
                message,
                certificate,
                profile_mode,
            ),
        )
        self._conn.commit()

    def recent(self, limit: int = 200) -> list[HistoryRecord]:
        cur = self._conn.execute(
            "SELECT id, ts, input_path, output_path, status, error_code, message, "
            "certificate, profile_mode FROM signing_history ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        rows = cur.fetchall()
        return [
            HistoryRecord(
                id=r[0],
                ts=r[1],
                input_path=r[2],
                output_path=r[3],
                status=r[4],
                error_code=r[5],
                message=r[6] or "",
                certificate=r[7],
                profile_mode=r[8],
            )
            for r in rows
        ]

    def export_csv(self, dest: Path) -> Path:
        import csv

        dest = Path(dest)
        with dest.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(
                [
                    "ts",
                    "input_path",
                    "output_path",
                    "status",
                    "error_code",
                    "message",
                    "certificate",
                    "profile_mode",
                ]
            )
            for rec in self.recent(10000):
                w.writerow(
                    [
                        rec.ts,
                        rec.input_path,
                        rec.output_path or "",
                        rec.status,
                        rec.error_code or "",
                        rec.message,
                        rec.certificate or "",
                        rec.profile_mode or "",
                    ]
                )
        return dest

    def close(self) -> None:
        self._conn.close()
