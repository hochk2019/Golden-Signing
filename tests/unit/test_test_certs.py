"""Unit tests for ephemeral RSA test certificate helper (T5, lab only)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from golden_signing.signing.test_certs import (
    certificate_fingerprint_sha256,
    generate_test_certificate,
    to_simple_signer,
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Candidate names of key material that must never appear under the repo.
KEY_FILE_PATTERNS = ("*.pem", "*.key", "*.p12", "*.pfx")


def _snapshot_repo_sensitive(root) -> set[str]:
    """Collect existing key-like files under repo paths for before/after comparison."""
    found: set[str] = set()
    for pattern in KEY_FILE_PATTERNS:
        for p in root.rglob(pattern):
            # ignore virtualenv and caches
            parts = {part.lower() for part in p.parts}
            if ".venv" in parts or ".mypy_cache" in parts or ".ruff_cache" in parts:
                continue
            if ".pytest_cache" in parts or "node_modules" in parts:
                continue
            found.add(str(p))
    return found


def test_generate_returns_certificate_and_private_key() -> None:
    cert, key = generate_test_certificate()
    assert isinstance(cert, x509.Certificate)
    assert isinstance(key, rsa.RSAPrivateKey)


def test_certificate_is_self_signed_with_expected_cn() -> None:
    cert, _key = generate_test_certificate(common_name="Golden Signing Test")
    subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    issuer_cn = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    assert "Golden Signing Test" in str(subject_cn)
    assert subject_cn == issuer_cn


def test_key_size_is_2048_by_default() -> None:
    cert, key = generate_test_certificate()
    assert key.key_size == 2048
    assert cert.public_key().key_size == 2048  # type: ignore[union-attr]


def test_fingerprint_is_64_lowercase_hex_chars() -> None:
    cert, _key = generate_test_certificate()
    fp = certificate_fingerprint_sha256(cert)
    assert isinstance(fp, str)
    assert HEX64.match(fp) is not None
    assert fp == fp.lower()
    assert ":" not in fp


def test_fingerprint_stable_for_same_cert() -> None:
    cert, _key = generate_test_certificate()
    assert certificate_fingerprint_sha256(cert) == certificate_fingerprint_sha256(cert)


def test_validity_window_is_short_and_ordered() -> None:
    cert, _key = generate_test_certificate()
    before = cert.not_valid_before_utc
    after = cert.not_valid_after_utc
    assert before < after
    now = datetime.now(UTC)
    assert before <= now + timedelta(minutes=1)
    assert before >= now - timedelta(days=2)
    # short lab window: ~30 days ahead
    assert timedelta(days=25) <= (after - now) <= timedelta(days=32)


def test_no_private_key_material_written_under_repo(tmp_path) -> None:
    """Generation must be in-memory: no new key-like files under the repo tree."""
    repo = tmp_path  # run with cwd isolation via monkeypatch below if needed
    # Use the project root (parent of tests/) for the scan.
    project_root = _project_root()
    before = _snapshot_repo_sensitive(project_root)
    generate_test_certificate()
    after = _snapshot_repo_sensitive(project_root)
    assert after == before
    # sanity: helper itself must not touch tmp_path either
    assert list(tmp_path.iterdir()) == []
    assert repo == tmp_path


def test_private_key_serializes_in_memory_only() -> None:
    """Key object supports in-memory PEM serialization (pyHanko path) without disk I/O."""
    _cert, key = generate_test_certificate()
    pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )
    assert b"-----BEGIN PRIVATE KEY-----" in pem
    assert b"-----BEGIN PUBLIC KEY-----" in pub


def _project_root():
    from pathlib import Path

    # tests/unit/test_test_certs.py -> repo root
    return Path(__file__).resolve().parents[2]


def test_to_simple_signer_builds_pyhanko_signer_in_memory() -> None:
    """T5 acceptance: cert/key are usable by pyHanko without touching disk."""
    cert, key = generate_test_certificate()
    signer = to_simple_signer(cert, key)
    assert "Golden Signing Test" in signer.subject_name
    sig = signer.sign_raw(b"golden-signing-lab", "sha256")
    assert isinstance(sig, bytes)
    assert len(sig) == 256  # RSA-2048 raw signature
