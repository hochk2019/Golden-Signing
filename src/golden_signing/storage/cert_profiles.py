"""Per-certificate signing appearance profiles (JSON store)."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["CertProfile", "CertProfileStore", "default_store_path"]


def default_store_path() -> Path:
    """%LOCALAPPDATA%/GoldenSigning/cert_profiles.json on Windows."""
    base = Path.home() / "AppData" / "Local" / "GoldenSigning"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path.home() / ".golden-signing"
        base.mkdir(parents=True, exist_ok=True)
    return base / "cert_profiles.json"


@dataclass
class CertProfile:
    """Appearance + mode settings bound to one certificate fingerprint."""

    fingerprint: str
    company: str = ""
    text_color_key: str = "navy"
    show_logo: bool = False
    logo_path: str = ""
    show_background: bool = True
    signature_mode: str = "visible"  # visible | invisible
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CertProfile:
        return cls(
            fingerprint=str(data.get("fingerprint") or ""),
            company=str(data.get("company") or ""),
            text_color_key=str(data.get("text_color_key") or "navy"),
            show_logo=bool(data.get("show_logo", False)),
            logo_path=str(data.get("logo_path") or ""),
            show_background=bool(data.get("show_background", True)),
            signature_mode=str(data.get("signature_mode") or "visible"),
            updated_at=float(data.get("updated_at") or time.time()),
        )


class CertProfileStore:
    """Load/save cert profiles keyed by SHA-256 fingerprint."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_store_path()
        self._data: dict[str, CertProfile] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            items = raw.get("profiles") or {}
            for fp, item in items.items():
                if isinstance(item, dict):
                    self._data[str(fp)] = CertProfile.from_dict({**item, "fingerprint": str(fp)})
        except Exception:  # noqa: BLE001
            self._data = {}

    def _save(self) -> None:
        payload = {
            "version": 1,
            "profiles": {fp: p.to_dict() for fp, p in self._data.items()},
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def get(self, fingerprint: str | None) -> CertProfile | None:
        if not fingerprint:
            return None
        return self._data.get(fingerprint)

    def upsert(self, profile: CertProfile) -> None:
        if not profile.fingerprint:
            return
        profile.updated_at = time.time()
        self._data[profile.fingerprint] = profile
        self._save()

    def all(self) -> list[CertProfile]:
        return sorted(self._data.values(), key=lambda p: -p.updated_at)
