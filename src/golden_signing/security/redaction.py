"""Strip secrets (PIN, private keys) from log lines and error messages."""

from __future__ import annotations

import logging
import re

__all__ = ["REDACTED", "RedactingFilter", "redact", "setup_app_logging"]

REDACTED = "***"

# PEM private-key blocks (any label) → single marker.
_PEM_BLOCK = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
# key=value / key: value where key mentions pin/password/secret/passphrase.
_KV_SECRET = re.compile(
    r"(?i)\b(pin|user_pin|userpin|password|passphrase|secret|private_key|privatekey)\b"
    r"(\s*[=:]\s*)"
    r"([^\s,;\"']+)"
)
# Bare 6–8 digit PIN next to the word PIN (e.g. "PIN 123456 failed").
_BARE_PIN = re.compile(
    r"(?i)\b(pin)\b(\s+)(\d{6,8})\b"
)


def redact(text: str) -> str:
    """Return text with PIN/key material replaced by REDACTED."""
    if not text:
        return text
    out = _PEM_BLOCK.sub(REDACTED, text)
    out = _KV_SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", out)
    out = _BARE_PIN.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", out)
    return out


class RedactingFilter(logging.Filter):
    """Apply redact() to the formatted message of every record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        cleaned = redact(msg)
        if cleaned != msg:
            record.msg = cleaned
            record.args = ()
        if record.exc_info:
            # Keep type/trace structure; scrub traceback text via format-time is hard.
            # Callers should redact before raise when embedding secrets.
            pass
        return True


def setup_app_logging(
    log_dir: object | None = None,
    *,
    level: int = logging.INFO,
) -> object:
    """Install a file handler with RedactingFilter. Idempotent per logger name."""
    from pathlib import Path

    logger = logging.getLogger("golden_signing")
    logger.setLevel(level)
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return logger

    if log_dir is None:
        from golden_signing.storage.app_paths import data_dir

        log_dir = data_dir() / "logs"
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path / "app.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    return logger
