"""Sign PDFs via Windows certificate store CSP (no PKCS#11)."""

from __future__ import annotations

import hashlib
import sys
from typing import Any

from golden_signing.signing.exceptions import TokenError

__all__ = ["WindowsCspSigner", "csp_sign_digest", "load_store_der_by_serial"]

_DIGEST_SIZES = {16: "md5", 20: "sha1", 32: "sha256", 48: "sha384", 64: "sha512"}


def load_store_der_by_serial(serial: str) -> bytes | None:
    """DER of CurrentUser\\My cert matching serial (hex, ignore case/leading zeros)."""
    if not serial or not sys.platform.startswith("win"):
        return None
    import base64
    import json
    import subprocess
    import tempfile
    from pathlib import Path

    s = serial.replace("'", "").replace(" ", "")
    # Compare normalized serials in PowerShell (strip leading zeros, upper)
    script = f"""
$want = ('{s}').ToUpperInvariant() -replace '^0+',''
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
$store.Open('ReadOnly')
$hit = $null
foreach($c in $store.Certificates){{
  $sn = $c.SerialNumber.ToUpperInvariant() -replace '^0+',''
  if($sn -eq $want) {{ $hit = $c; break }}
}}
$store.Close()
if($hit -eq $null) {{ Write-Output 'ERR:NO_CERT'; exit 0 }}
[Convert]::ToBase64String($hit.RawData)
"""
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=25,
            check=False,
            creationflags=0x08000000,
        )
    except Exception:  # noqa: BLE001
        return None
    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text or text.startswith("ERR:"):
        return None
    # PowerShell may wrap long base64
    text = "".join(text.split())
    try:
        return base64.b64decode(text)
    except Exception:  # noqa: BLE001
        return None


def _hash_data(data: bytes, digest_algorithm: str) -> bytes:
    name = (digest_algorithm or "sha256").lower().replace("-", "")
    if name in ("sha256", "sha1", "sha384", "sha512", "md5"):
        return hashlib.new(name, data).digest()
    return hashlib.sha256(data).digest()


def csp_sign_digest(digest: bytes, serial: str) -> bytes:
    """RSA-PKCS1 sign a digest via Windows CSP/CNG (CurrentUser store)."""
    if not sys.platform.startswith("win"):
        raise TokenError("Windows CSP chỉ hỗ trợ trên Windows", code="CSP_UNSUPPORTED")
    if not load_store_der_by_serial(serial):
        raise TokenError(
            f"Không tìm thấy CKS serial {serial} trong Windows cert store (CurrentUser\\My).",
            code="CSP_CERT_MISSING",
        )
    import base64
    import subprocess
    import tempfile
    from pathlib import Path

    digest_b64 = base64.b64encode(digest).decode("ascii")
    with tempfile.TemporaryDirectory(prefix="gs-csp-") as td:
        outp = Path(td) / "sig.bin"
        out_win = str(outp).replace("\\", "/")
        script = f"""
$serial = '{serial}'
$digest = [Convert]::FromBase64String('{digest_b64}')
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
$store.Open('ReadOnly')
$cert = $null
foreach($c in $store.Certificates){{
  $sn = $c.SerialNumber
  if($sn -eq $serial -or ($sn -replace '^0','') -eq ($serial -replace '^0','')) {{ $cert = $c; break }}
}}
$store.Close()
if($cert -eq $null) {{ Write-Output 'ERR:NO_CERT'; exit 1 }}
if(-not $cert.HasPrivateKey) {{ Write-Output 'ERR:NO_KEY'; exit 1 }}
$rsa = $null
try {{
  $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
}} catch {{ $rsa = $null }}
if($null -eq $rsa) {{
  try {{ $rsa = $cert.PrivateKey }} catch {{ $rsa = $null }}
}}
if($null -eq $rsa) {{ Write-Output 'ERR:NO_RSA'; exit 1 }}
try {{
  $sig = $rsa.SignHash($digest, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
  [IO.File]::WriteAllBytes('{out_win}', $sig)
  Write-Output ('OK:' + $sig.Length)
}} catch {{
  try {{
    $sig = $rsa.SignData($digest, [Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256'))
    [IO.File]::WriteAllBytes('{out_win}', $sig)
    Write-Output ('OK:' + $sig.Length)
  }} catch {{
    Write-Output ('ERR:' + $_.Exception.Message)
  }}
}}
"""
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
                creationflags=0x08000000,
            )
        except Exception as e:  # noqa: BLE001
            raise TokenError(f"CSP/.NET ký thất bại: {e}", code="CSP_SIGN_FAILED") from e
        out = (proc.stdout or "").strip()
        if not out.startswith("OK:") or not outp.is_file():
            raise TokenError(
                f"CSP/.NET không ký được CKS serial {serial}: {out or (proc.stderr or '')[:200]}",
                code="CSP_SIGN_FAILED",
            )
        return outp.read_bytes()


from pyhanko.sign.signers import Signer as _PyHankoSigner


class WindowsCspSigner(_PyHankoSigner):
    """pyHanko Signer for Windows store certs (CSP/CNG private key)."""

    def __init__(self, signing_cert_asn1: Any, serial: str) -> None:
        super().__init__(
            prefer_pss=False,
            embed_roots=True,
            signing_cert=signing_cert_asn1,
            cert_registry=None,
        )
        self._gs_serial = serial
        self._gs_signing_cert = signing_cert_asn1

    def estimate_raw_signature_size_bytes(self) -> int:
        try:
            cert = self.signing_cert
            if cert is not None:
                key = cert.public_key
                # asn1crypto: certificate['tbs_certificate']['subject_public_key_info']
                spki = cert["tbs_certificate"]["subject_public_key_info"]
                if str(spki.algorithm) == "rsa":
                    mod = int(spki["public_key"].native["modulus"])
                    return (mod.bit_length() + 7) // 8
        except Exception:  # noqa: BLE001
            pass
        return 256

    def _to_digest(self, data: bytes, digest_algorithm: str) -> bytes:
        if len(data) in _DIGEST_SIZES:
            return data
        return _hash_data(data, digest_algorithm)

    async def async_sign_raw(
        self, data: bytes, digest_algorithm: str = "sha256", dry_run: bool = False
    ) -> bytes:
        if dry_run:
            return self.estimate_raw_signature_size_bytes() * b"\x00"
        digest = self._to_digest(data, digest_algorithm)
        return csp_sign_digest(digest, self._gs_serial)

    def sign_raw(
        self, data: bytes, digest_algorithm: str = "sha256", dry_run: bool = False
    ) -> bytes:
        if dry_run:
            return self.estimate_raw_signature_size_bytes() * b"\x00"
        digest = self._to_digest(data, digest_algorithm)
        return csp_sign_digest(digest, self._gs_serial)
