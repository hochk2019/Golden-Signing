"""Download, verify, stage, and rollback update packages."""

from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from golden_signing.updater.verify import file_sha256, verify_file_sha256

__all__ = [
    "ApplyResult",
    "UpdateApplyError",
    "default_update_dir",
    "download_file",
    "extract_zip",
    "backup_app_dir",
    "restore_previous",
    "stage_update",
]


class UpdateApplyError(RuntimeError):
    """Download/verify/extract/rollback failure."""


@dataclass(frozen=True, slots=True)
class ApplyResult:
    zip_path: Path
    extract_dir: Path
    backup_dir: Path | None


def default_update_dir() -> Path:
    from golden_signing.storage.app_paths import data_dir

    return data_dir() / "updates"


def download_file(
    url: str,
    dest: Path,
    *,
    timeout: float = 120.0,
    getter: Callable[[str, float], bytes] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Download url → dest. on_progress(done_bytes, total_bytes_or_0)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if getter is not None:
        data = getter(url, timeout)
        dest.write_bytes(data)
        if on_progress is not None:
            on_progress(len(data), len(data))
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "GoldenSigning-Updater"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:  # noqa: S310
            total = 0
            cl = resp.headers.get("Content-Length")
            if cl and cl.isdigit():
                total = int(cl)
            done = 0
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if on_progress is not None:
                    on_progress(done, total)
    except Exception as exc:  # noqa: BLE001
        raise UpdateApplyError(f"tải thất bại: {exc}") from exc
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile as exc:
        raise UpdateApplyError("file zip hỏng") from exc
    return dest_dir


def backup_app_dir(app_dir: Path, update_root: Path) -> Path | None:
    """Copy app_dir → update_root/previous (replace old backup). None if app_dir missing."""
    if not app_dir.is_dir():
        return None
    prev = update_root / "previous"
    if prev.exists():
        shutil.rmtree(prev, ignore_errors=True)
    prev.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(app_dir, prev)
    except OSError as exc:
        raise UpdateApplyError(f"backup thất bại: {exc}") from exc
    return prev


def restore_previous(update_root: Path, app_dir: Path) -> bool:
    """Restore update_root/previous into app_dir. True if restored."""
    prev = update_root / "previous"
    if not prev.is_dir():
        return False
    if app_dir.exists():
        shutil.rmtree(app_dir, ignore_errors=True)
    try:
        shutil.copytree(prev, app_dir)
    except OSError as exc:
        raise UpdateApplyError(f"rollback thất bại: {exc}") from exc
    return True


def stage_update(
    *,
    zip_url: str,
    expected_sha256: str,
    version_tag: str,
    app_dir: Path | None,
    update_root: Path | None = None,
    download: Callable[[str, Path], Path] | None = None,
    on_download_progress: Callable[[int, int], None] | None = None,
) -> ApplyResult:
    """
    Download zip → verify SHA256 → extract to updates/staged-<ver> →
    backup app_dir to updates/previous. Does not replace the live app.
    """
    root = update_root or default_update_dir()
    root.mkdir(parents=True, exist_ok=True)
    safe_tag = "".join(c if c.isalnum() or c in "._-" else "_" for c in version_tag)
    zip_path = root / f"download-{safe_tag}.zip"
    extract_dir = root / f"staged-{safe_tag}"

    if download is not None:
        download(zip_url, zip_path)
    else:
        download_file(zip_url, zip_path, on_progress=on_download_progress)

    if not expected_sha256:
        raise UpdateApplyError("thiếu SHA256 trên release — không cài")
    if not verify_file_sha256(zip_path, expected_sha256):
        actual = file_sha256(zip_path)
        zip_path.unlink(missing_ok=True)
        raise UpdateApplyError(
            f"SHA256 không khớp (kỳ vọng {expected_sha256[:12]}…, nhận {actual[:12]}…)"
        )

    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    extract_zip(zip_path, extract_dir)

    backup = backup_app_dir(app_dir, root) if app_dir is not None else None

    meta = {
        "version": version_tag,
        "zip": zip_path.name,
        "sha256": expected_sha256,
        "staged": extract_dir.name,
        "app_dir": str(app_dir) if app_dir else "",
    }
    (root / "staged.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ApplyResult(zip_path=zip_path, extract_dir=extract_dir, backup_dir=backup)


def _tmp_marker(root: Path) -> Path:
    return root / "apply_in_progress"


def apply_staged_swap(
    *,
    staged_dir: Path,
    app_dir: Path,
    update_root: Path,
    relaunch: list[str] | None = None,
) -> None:
    """
    Replace app_dir contents with staged_dir. For onedir layouts.
    Writes a marker; on failure attempts restore_previous.
    """
    marker = _tmp_marker(update_root)
    marker.write_text(staged_dir.name, encoding="utf-8")
    try:
        # Move live aside then promote staged
        trash = update_root / "old-live"
        if trash.exists():
            shutil.rmtree(trash, ignore_errors=True)
        if app_dir.exists():
            app_dir.rename(trash)
        shutil.copytree(staged_dir, app_dir)
        marker.unlink(missing_ok=True)
    except OSError as exc:
        restore_previous(update_root, app_dir)
        marker.unlink(missing_ok=True)
        raise UpdateApplyError(f"thay thư mục app thất bại, đã rollback: {exc}") from exc
