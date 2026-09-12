"""GitHub Releases latest lookup (stdlib urllib; injectable for tests)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from golden_signing.updater.version import Version, parse_version

__all__ = ["UpdateInfo", "UpdateSourceError", "fetch_latest_release"]

_DEFAULT_TIMEOUT = 15.0
_USER_AGENT = "GoldenSigning-Updater"


class UpdateSourceError(RuntimeError):
    """Network/API/parse failure while checking for updates."""


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: Version
    tag: str
    html_url: str
    body: str
    zip_name: str | None
    zip_url: str | None
    checksums: dict[str, str] = field(default_factory=dict)

    def zip_sha256(self) -> str | None:
        if not self.zip_name:
            return None
        return self.checksums.get(self.zip_name)


def _default_get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise UpdateSourceError(f"HTTP {exc.code} từ GitHub") from exc
    except urllib.error.URLError as exc:
        raise UpdateSourceError(f"Không kết nối được GitHub: {exc.reason}") from exc


def _pick_zip(assets: list[dict]) -> tuple[str | None, str | None]:
    """Return (name, browser_download_url) preferring win64 GoldenSigning zip."""
    zips = [
        a
        for a in assets
        if str(a.get("name", "")).lower().endswith(".zip")
        and "goldensigning" in str(a.get("name", "")).lower()
    ]
    if not zips:
        zips = [a for a in assets if str(a.get("name", "")).lower().endswith(".zip")]
    if not zips:
        return None, None
    win = [a for a in zips if "win64" in str(a.get("name", "")).lower()]
    chosen = win[0] if win else zips[0]
    return str(chosen.get("name") or None), str(chosen.get("browser_download_url") or None)


def parse_release_json(payload: bytes | str) -> UpdateInfo:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise UpdateSourceError("GitHub trả về JSON không hợp lệ") from exc
    if not isinstance(data, dict):
        raise UpdateSourceError("GitHub payload không phải object")
    tag = str(data.get("tag_name") or "")
    if not tag:
        raise UpdateSourceError("Release không có tag_name")
    version = parse_version(tag)
    assets = data.get("assets") or []
    if not isinstance(assets, list):
        assets = []
    zip_name, zip_url = _pick_zip(assets)
    return UpdateInfo(
        version=version,
        tag=tag,
        html_url=str(data.get("html_url") or ""),
        body=str(data.get("body") or ""),
        zip_name=zip_name,
        zip_url=zip_url,
        checksums={},  # filled by caller after downloading checksums.txt
    )


def fetch_latest_release(
    repo: str,
    *,
    get: Callable[[str, float], bytes] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> UpdateInfo:
    """Fetch /releases/latest for 'owner/name'."""
    repo = (repo or "").strip().strip("/")
    if repo.count("/") != 1 or not all(repo.split("/")):
        raise UpdateSourceError("repo phải dạng owner/name")
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    getter = get or _default_get
    try:
        raw = getter(url, timeout)
    except UpdateSourceError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UpdateSourceError(str(exc)) from exc
    return parse_release_json(raw)
