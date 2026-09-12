"""SHA256 checksum file parsing and file verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = ["file_sha256", "parse_checksums", "verify_file_sha256"]


def file_sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def parse_checksums(text: str) -> dict[str, str]:
    """Parse GNU coreutils-style checksums.txt: '<hash>  <filename>'."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # binary mode marker '*' optional
        parts = line.split()
        if len(parts) < 2:
            continue
        digest = parts[0].lower()
        name = parts[-1].lstrip("*")
        if len(digest) == 64 and all(c in "0123456789abcdef" for c in digest):
            out[name] = digest
    return out


def verify_file_sha256(path: Path, expected: str) -> bool:
    return file_sha256(path).lower() == expected.strip().lower()
