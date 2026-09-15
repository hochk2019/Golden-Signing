"""Phase 8 updater unit tests (no network)."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from golden_signing.updater.apply import (
    InstallerResult,
    UpdateApplyError,
    backup_app_dir,
    restore_previous,
    stage_installer,
    stage_update,
)
from golden_signing.updater.github import (
    UpdateSourceError,
    fetch_latest_release,
    parse_release_json,
)
from golden_signing.updater.verify import file_sha256, parse_checksums, verify_file_sha256
from golden_signing.updater.version import parse_version


def test_parse_version_orders() -> None:
    assert parse_version("v1.2.3") > parse_version("1.2.2")
    assert parse_version("1.2.3") == parse_version("v1.2.3")
    assert parse_version("0.1.0") > parse_version("0.1.0a0")
    assert parse_version("1.2") == parse_version("1.2.0")


def test_parse_release_json_picks_win64_zip() -> None:
    payload = {
        "tag_name": "v1.4.0",
        "html_url": "https://github.com/o/r/releases/tag/v1.4.0",
        "body": "notes",
        "assets": [
            {
                "name": "GoldenSign-1.4.0-linux.zip",
                "browser_download_url": "https://example/linux.zip",
            },
            {
                "name": "GoldenSign-1.4.0-win64.zip",
                "browser_download_url": "https://example/win64.zip",
            },
            {
                "name": "GoldenSign-Setup-1.4.0.exe",
                "browser_download_url": "https://example/setup.exe",
            },
            {"name": "checksums.txt", "browser_download_url": "https://example/c.txt"},
        ],
    }
    info = parse_release_json(json.dumps(payload))
    assert info.version.raw == "v1.4.0"
    assert info.zip_name == "GoldenSign-1.4.0-win64.zip"
    assert info.zip_url == "https://example/win64.zip"
    assert info.installer_name == "GoldenSign-Setup-1.4.0.exe"
    assert info.installer_url == "https://example/setup.exe"


def test_fetch_latest_release_uses_injected_get() -> None:
    payload = {
        "tag_name": "v2.0.0",
        "html_url": "https://x",
        "assets": [],
    }
    seen: list[str] = []

    def get(url: str, timeout: float) -> bytes:
        seen.append(url)
        return json.dumps(payload).encode()

    info = fetch_latest_release("hockh/golden-signing", get=get)
    assert info.version.raw == "v2.0.0"
    assert seen and seen[0].endswith("/repos/hockh/golden-signing/releases/latest")


def test_fetch_latest_release_rejects_bad_repo() -> None:
    with pytest.raises(UpdateSourceError):
        fetch_latest_release("noslash")


def test_parse_checksums_and_verify(tmp_path: Path) -> None:
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")
    digest = hashlib.sha256(b"hello").hexdigest()
    table = parse_checksums(f"{digest}  GoldenSigning-1.0.0-win64.zip\n")
    assert table["GoldenSigning-1.0.0-win64.zip"] == digest
    assert verify_file_sha256(f, digest) is True
    assert verify_file_sha256(f, "0" * 64) is False
    assert file_sha256(f) == digest


def _make_zip(path: Path, inner: str = "GoldenSigning/app.exe") -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(inner, b"binary-content")
    data = buf.getvalue()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_stage_update_verifies_and_backs_up(tmp_path: Path) -> None:
    zip_path = tmp_path / "pkg.zip"
    digest = _make_zip(zip_path)
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "old.txt").write_text("old", encoding="utf-8")
    update_root = tmp_path / "updates"

    def download(url: str, dest: Path) -> Path:
        dest.write_bytes(zip_path.read_bytes())
        return dest

    result = stage_update(
        zip_url="https://example/pkg.zip",
        expected_sha256=digest,
        version_tag="v9.9.9",
        app_dir=app_dir,
        update_root=update_root,
        download=download,  # type: ignore[arg-type]
    )
    assert result.extract_dir.is_dir()
    assert (result.extract_dir / "GoldenSigning" / "app.exe").is_file()
    assert result.backup_dir is not None
    assert (result.backup_dir / "old.txt").read_text(encoding="utf-8") == "old"
    assert (update_root / "staged.json").is_file()


def test_stage_update_rejects_bad_hash(tmp_path: Path) -> None:
    zip_path = tmp_path / "pkg.zip"
    _make_zip(zip_path)
    update_root = tmp_path / "updates"

    def download(url: str, dest: Path) -> Path:
        dest.write_bytes(zip_path.read_bytes())
        return dest

    with pytest.raises(UpdateApplyError, match="SHA256"):
        stage_update(
            zip_url="https://example/pkg.zip",
            expected_sha256="0" * 64,
            version_tag="v9.9.9",
            app_dir=None,
            update_root=update_root,
            download=download,  # type: ignore[arg-type]
        )
    assert not (update_root / "download-v9.9.9.zip").exists()


def test_stage_update_requires_hash(tmp_path: Path) -> None:
    zip_path = tmp_path / "pkg.zip"
    _make_zip(zip_path)

    def download(url: str, dest: Path) -> Path:
        dest.write_bytes(zip_path.read_bytes())
        return dest

    with pytest.raises(UpdateApplyError, match="thiếu SHA256"):
        stage_update(
            zip_url="https://example/pkg.zip",
            expected_sha256="",
            version_tag="v1",
            app_dir=None,
            update_root=tmp_path / "u",
            download=download,  # type: ignore[arg-type]
        )


def test_stage_installer_verifies_and_backs_up(tmp_path: Path) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"installer")
    digest = hashlib.sha256(b"installer").hexdigest()
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "old.txt").write_text("old", encoding="utf-8")

    def download(url: str, dest: Path) -> Path:
        dest.write_bytes(installer.read_bytes())
        return dest

    result = stage_installer(
        installer_url="https://example/setup.exe",
        expected_sha256=digest,
        version_tag="v9.9.9",
        app_dir=app_dir,
        update_root=tmp_path / "updates",
        download=download,  # type: ignore[arg-type]
    )
    assert isinstance(result, InstallerResult)
    assert result.installer_path.is_file()
    assert result.backup_dir is not None
    assert (result.backup_dir / "old.txt").read_text(encoding="utf-8") == "old"


def test_backup_and_restore_previous(tmp_path: Path) -> None:
    app = tmp_path / "live"
    app.mkdir()
    (app / "x.txt").write_text("live", encoding="utf-8")
    root = tmp_path / "updates"
    prev = backup_app_dir(app, root)
    assert prev is not None
    (app / "x.txt").write_text("broken", encoding="utf-8")
    assert restore_previous(root, app) is True
    assert (app / "x.txt").read_text(encoding="utf-8") == "live"


def test_check_for_update_newer_with_checksums() -> None:
    from golden_signing.updater.check import check_for_update

    zip_name = "GoldenSigning-9.0.0-win64.zip"
    digest = "a" * 64
    payload = {
        "tag_name": "v9.0.0",
        "html_url": "https://github.com/o/r/releases/tag/v9.0.0",
        "assets": [
            {"name": zip_name, "browser_download_url": "https://example/z.zip"},
            {
                "name": "checksums.txt",
                "browser_download_url": "https://example/checksums.txt",
            },
        ],
    }

    def get(url: str, timeout: float) -> bytes:
        if url.endswith("checksums.txt"):
            return f"{digest}  {zip_name}\n".encode()
        return json.dumps(payload).encode()

    result = check_for_update(
        "owner/repo", local_version="1.0.0", get=get
    )
    assert result.ok
    assert result.newer is True
    assert result.info is not None
    assert result.info.zip_sha256() == digest
    assert result.info.tag == "v9.0.0"


def test_check_for_update_same_version() -> None:
    from golden_signing.updater.check import check_for_update

    payload = {"tag_name": "v1.0.0", "html_url": "https://x", "assets": []}
    result = check_for_update(
        "owner/repo",
        local_version="1.0.0",
        get=lambda url, timeout: json.dumps(payload).encode(),
    )
    assert result.ok
    assert result.newer is False


def test_check_for_update_missing_repo() -> None:
    from golden_signing.updater.check import check_for_update

    result = check_for_update("", local_version="1.0.0", get=lambda u, t: b"{}")
    assert result.ok is False
    assert result.error
    assert "repo" in result.error.lower() or "GitHub" in result.error
