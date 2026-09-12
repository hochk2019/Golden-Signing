"""Version parse/compare for update checks."""

from __future__ import annotations

import re

__all__ = ["Version", "parse_version"]

_NUM = re.compile(r"\d+")


class Version:
    """Minimal PEP 440-ish version: major.minor.patch + optional pre tag."""

    __slots__ = ("parts", "pre", "raw")

    def __init__(self, parts: tuple[int, ...], pre: str | None, raw: str) -> None:
        self.parts = parts
        self.pre = pre
        self.raw = raw

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other: Version) -> bool:
        return self._key() < other._key()

    def __le__(self, other: Version) -> bool:
        return self._key() <= other._key()

    def __gt__(self, other: Version) -> bool:
        return self._key() > other._key()

    def __ge__(self, other: Version) -> bool:
        return self._key() >= other._key()

    def __repr__(self) -> str:
        return f"Version({self.raw!r})"

    def _key(self) -> tuple:
        # Release > pre-release of same numbers (0.1.0 > 0.1.0a0)
        pre_key = (1, "") if self.pre is None else (0, self.pre)
        return (self.parts, pre_key)


def parse_version(text: str) -> Version:
    """Parse 'v1.2.3', '1.2.3', '0.1.0a0', 'v1.2.3-beta.1'."""
    raw = text.strip()
    if raw.lower().startswith("v"):
        raw = raw[1:]
    raw = raw.strip()
    if not raw:
        raise ValueError("empty version")
    m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", raw)
    if not m:
        raise ValueError(f"invalid version: {text!r}")
    nums = tuple(int(x) for x in _NUM.findall(m.group(1)))
    # pad to at least 3 components for stable compare
    while len(nums) < 3:
        nums = (*nums, 0)
    pre = m.group(2).strip() or None
    if pre and pre[0] in ".-_":
        pre = pre[1:] or None
    return Version(nums, pre, text.strip())
