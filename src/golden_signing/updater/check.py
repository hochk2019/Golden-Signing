"""High-level update check: latest release + checksums + compare to local."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace

from golden_signing import __version__
from golden_signing.updater.github import (
    UpdateInfo,
    UpdateSourceError,
    _default_get,
    parse_release_json,
)
from golden_signing.updater.verify import parse_checksums
from golden_signing.updater.version import Version, parse_version

__all__ = ["DEFAULT_UPDATE_REPO", "CheckResult", "check_for_update", "resolve_repo"]

DEFAULT_UPDATE_REPO = "hochk2019/Golden-Signing"


def resolve_repo(configured: str | None) -> str:
    """Prefer QSettings value; fall back to the public GitHub repo slug."""
    text = (configured or "").strip()
    return text if text else DEFAULT_UPDATE_REPO


class CheckResult:
    """Outcome of a manual update check."""

    def __init__(
        self,
        *,
        info: UpdateInfo | None,
        local: Version,
        newer: bool,
        error: str | None = None,
    ) -> None:
        self.info = info
        self.local = local
        self.newer = newer
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None


def _checksums_url(assets: object) -> str | None:
    if not isinstance(assets, list):
        return None
    for a in assets:
        if not isinstance(a, dict):
            continue
        name = str(a.get("name") or "").lower()
        if name in ("checksums.txt", "sha256sums", "sha256sums.txt"):
            url = a.get("browser_download_url")
            if url:
                return str(url)
    return None


def check_for_update(
    repo: str,
    *,
    local_version: str | None = None,
    get: Callable[[str, float], bytes] | None = None,
    timeout: float = 15.0,
) -> CheckResult:
    """Fetch latest release once; attach checksums.txt map; compare versions."""
    local = parse_version(local_version or __version__)
    repo = (repo or "").strip().strip("/")
    getter = get or _default_get
    if repo.count("/") != 1 or not all(repo.split("/")):
        return CheckResult(
            info=None, local=local, newer=False, error="Chưa cấu hình repo GitHub (owner/name)"
        )
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        raw = getter(url, timeout)
        info = parse_release_json(raw)
        try:
            data = json.loads(raw)
            assets = data.get("assets") if isinstance(data, dict) else None
        except json.JSONDecodeError:
            assets = None
        csum_url = _checksums_url(assets)
        checksums: dict[str, str] = {}
        if csum_url:
            try:
                text = getter(csum_url, timeout).decode("utf-8", errors="replace")
                checksums = parse_checksums(text)
            except Exception:  # noqa: BLE001
                checksums = {}
        info = replace(info, checksums=checksums)
        return CheckResult(info=info, local=local, newer=info.version > local)
    except UpdateSourceError as exc:
        return CheckResult(info=None, local=local, newer=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(info=None, local=local, newer=False, error=str(exc))
