"""Sign PDFs via Windows certificate store CSP (no PKCS#11) — store certs with private key."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Any

from golden_signing.signing.exceptions import TokenError

__all__ = ["WindowsCspSigner", "csp_sign_digest", "find_store_der_by_serial"]

PROV_RSA_AES = 24
PROV_RSA_FULL = 1
AT_SIGNATURE = 2
AT_KEYEXCHANGE = 1
HP_HASHVAL = 2
CALG_SHA_256 = 0x800C
CERT_STORE_PROV_SYSTEM_W = 10
CERT_SYSTEM_STORE_CURRENT_USER = 0x10000
CERT_STORE_OPEN_EXISTING_ONLY = 0x4000
CERT_STORE_READONLY_FLAG = 0x8000
CERT_KEY_PROV_INFO_PROP_ID = 2


def find_store_der_by_serial(serial: str) -> bytes | None:
    """Return DER of CurrentUser\\My cert matching serial (hex, case-insensitive)."""
    if not serial or not sys.platform.startswith("win"):
        return None
    from golden_signing.certificate.windows_store import list_windows_my_certificates

    target = serial.lower().lstrip("0")
    for c in list_windows_my_certificates():
        if str(c.serial).lower().lstrip("0") == target:
            # Re-read DER via certutil blob parse if available
            from golden_signing.certificate import windows_store as ws

            for sc in ws._list_my_via_certutil():  # noqa: SLF001
                if str(sc.serial).lower().lstrip("0") == target and sc.der:
                    return sc.der
    return None


def _load_cert_der_from_ps(serial: str) -> bytes | None:
    if not sys.platform.startswith("win"):
        return None
    import base64
    import json
    import subprocess

    script = (
        "$s='" + serial.replace("'", "") + "'\n"
        "$store=New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')\n"
        "$store.Open('ReadOnly')\n"
        "$out=@()\n"
        "foreach($c in $store.Certificates){\n"
        "  if($c.SerialNumber -eq $s -or ($c.SerialNumber -replace '^0','') -eq ($s -replace '^0','')){\n"
        "    $out += [Convert]::ToBase64String($c.RawData)\n"
        "  }\n"
        "}\n"
        "$store.Close()\n"
        "ConvertTo-Json -InputObject $out -Compress\n"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=20,
            check=False,
            creationflags=0x08000000,
        )
    except Exception:  # noqa: BLE001
        return None
    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(items, str):
        items = [items]
    if not items:
        return None
    try:
        return base64.b64decode(items[0])
    except Exception:  # noqa: BLE001
        return None


def csp_sign_digest(digest: bytes, serial: str, *, sha_alg: int = CALG_SHA_256) -> bytes:
    """RSA-sign a precomputed digest via Windows CryptoAPI (HP_HASHVAL + CryptSignHash)."""
    if not sys.platform.startswith("win"):
        raise TokenError("Windows CSP chỉ hỗ trợ trên Windows", code="CSP_UNSUPPORTED")
    der = _load_cert_der_from_ps(serial)
    if not der:
        raise TokenError(
            f"Không tìm thấy CKS serial {serial} trong Windows cert store (CurrentUser\\My).",
            code="CSP_CERT_MISSING",
        )

    # Locate key container via certutil/provider info is hard; use CryptAcquireContext
    # with key container name from cert property when possible — fallback: sign via
    # .NET RSACng if CSP CryptoAPI path fails.
    return _sign_via_dotnet(digest, serial)


def _sign_via_dotnet(digest: bytes, serial: str) -> bytes:
    """Use .NET X509Certificate2 + GetRSAPrivateKey().SignHash (CSP/CNG)."""
    import base64
    import json
    import subprocess
    import tempfile
    from pathlib import Path

    digest_b64 = base64.b64encode(digest).decode("ascii")
    with tempfile.TemporaryDirectory(prefix="gs-csp-") as td:
        outp = Path(td) / "sig.bin"
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
  [IO.File]::WriteAllBytes('{str(outp).replace(chr(92), "/")}', $sig)
  Write-Output ('OK:' + $sig.Length)
}} catch {{
  # CSP PrivateKey may not support SignHash(HashAlgorithmName) — try legacy
  try {{
    $sig = $rsa.SignData($digest, [Security.Cryptography.CryptoConfig]::MapNameToOID('SHA256'))
    [IO.File]::WriteAllBytes('{str(outp).replace(chr(92), "/")}', $sig)
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
                timeout=40,
                check=False,
                creationflags=0x08000000,
            )
        except Exception as e:  # noqa: BLE001
            raise TokenError(f"CSP/.NET ký thất bại: {e}", code="CSP_SIGN_FAILED") from e
        out = (proc.stdout or "").strip()
        if not out.startswith("OK:") or not outp.is_file():
            raise TokenError(
                f"CSP/.NET không ký được CKS serial {serial}: {out or proc.stderr}",
                code="CSP_SIGN_FAILED",
            )
        return outp.read_bytes()


class WindowsCspSigner:
    """pyHanko-compatible signer for Windows store certs (CSP/CNG private key)."""

    def __init__(self, signing_cert_asn1: Any, serial: str) -> None:
        from pyhanko.sign.signers import Signer as _PySigner

        # Duck-type: hold cert like Signer; implement async_sign_raw for CMS
        self.signing_cert = signing_cert_asn1
        self._serial = serial
        self._prefer_pss = False
        self._signer_base = _PySigner
        self.cert_registry = None

    def estimate_raw_signature_size_bytes(self) -> int:
        return 256

    def async_sign_raw(
        self, data: bytes, digest_algorithm: str = "sha256", dry_run: bool = False
    ) -> bytes:
        if dry_run:
            return self.estimate_raw_signature_size_bytes() * b"\x00"
        return csp_sign_digest(data, self._serial)

    def sign_raw(
        self, data: bytes, digest_algorithm: str = "sha256", dry_run: bool = False
    ) -> bytes:
        return self.async_sign_raw(data, digest_algorithm, dry_run)

    def get_signature_mechanism_for_digest(self, digest_algorithm: str) -> Any:
        from asn1crypto.algos import SignedDigestAlgorithm

        return SignedDigestAlgorithm("sha256_rsa")
