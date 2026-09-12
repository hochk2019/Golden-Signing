"""Log redaction — PIN and private keys must never appear in logs/messages."""

from __future__ import annotations

import logging

from golden_signing.security.redaction import (
    REDACTED,
    RedactingFilter,
    redact,
    setup_app_logging,
)


def test_redact_pin_key_value() -> None:
    assert "123456" not in redact("login failed pin=123456")
    assert "123456" not in redact("user_pin: 654321")
    assert REDACTED in redact("PIN=111222")


def test_redact_bare_pin() -> None:
    assert "998877" not in redact("PIN 998877 rejected")
    assert REDACTED in redact("PIN 998877 rejected")


def test_redact_pem_private_key() -> None:
    pem = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\n"
        "-----END PRIVATE KEY-----"
    )
    out = redact(f"dump {pem} end")
    assert "MIIEvQ" not in out
    assert REDACTED in out


def test_redact_keeps_mst_and_paths() -> None:
    text = "cert MST=2300944637 path C:\\docs\\file_2024.pdf"
    assert "2300944637" in redact(text)
    assert "file_2024.pdf" in redact(text)


def test_redacting_filter_on_logger(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    logger = setup_app_logging(log_dir)
    logger.info("attempt pin=424242")
    for h in logger.handlers:
        h.flush()
    content = (log_dir / "app.log").read_text(encoding="utf-8")
    assert "424242" not in content
    assert REDACTED in content
    # teardown handler so later tests don't hold the file
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


def test_filter_keeps_clean_messages() -> None:
    f = RedactingFilter()
    rec = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "signed ok %s", ("abc",), None
    )
    assert f.filter(rec) is True
    assert rec.getMessage() == "signed ok abc"
