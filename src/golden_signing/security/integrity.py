"""Atomic output helpers (spec §5.3). Never leave a 'signed' file if verify fails."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path


def atomic_write_bytes(
    final_path: Path,
    data: bytes,
    *,
    verify: Callable[[Path], bool] | None = None,
) -> Path:
    """Write bytes to a temp sibling, optional verify, fsync, then os.replace."""
    final_path = final_path.resolve()
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = final_path.with_name(f".{final_path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if verify is not None and not verify(tmp):
            raise ValueError(f"post-write verification failed for {final_path.name}")
        os.replace(tmp, final_path)
        return final_path
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
