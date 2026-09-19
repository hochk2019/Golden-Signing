"""Windows CSP signing — vendor PIN once per serial via long-lived session."""

from __future__ import annotations

import base64
import subprocess
import sys
import threading
from typing import Any

from golden_signing.signing.exceptions import TokenError
from pyhanko.sign.signers import Signer as _PyHankoSignerBase

__all__ = [
    "WindowsCspSigner",
    "csp_sign_digest",
    "load_store_der_by_serial",
    "clear_csp_cache",
    "CspSignSession",
]

_DIGEST_SIZES = {16, 20, 32, 48, 64}
_SESSIONS: dict[str, "CspSignSession"] = {}
_LOCK = threading.Lock()

# One GetRSAPrivateKey (vendor PIN UI once) then loop SignHash for the batch.
_PS_SESSION_SCRIPT = r"""
$serial = '{serial}'
$want = $serial.ToUpperInvariant() -replace '^0+',''
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
$store.Open('ReadOnly')
$cert = $null
foreach($c in $store.Certificates){{
  $sn = $c.SerialNumber.ToUpperInvariant() -replace '^0+',''
  if($sn -eq $want) {{ $cert = $c; break }}
}}
$store.Close()
if($cert -eq $null) {{ Write-Output 'ERR:NO_CERT'; [Console]::Out.Flush(); exit 1 }}
$rsa = $null
try {{ $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert) }} catch {{ $rsa = $null }}
if($null -eq $rsa) {{ try {{ $rsa = $cert.PrivateKey }} catch {{ $rsa = $null }} }}
if($null -eq $rsa) {{ Write-Output 'ERR:NO_RSA'; [Console]::Out.Flush(); exit 1 }}
Write-Output 'READY'
[Console]::Out.Flush()
while($true) {{
  $line = [Console]::In.ReadLine()
  if($null -eq $line -or $line -eq 'QUIT') {{ break }}
  try {{
    $digest = [Convert]::FromBase64String($line)
    $sig = $rsa.SignHash($digest, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    Write-Output ('OK:' + [Convert]::ToBase64String($sig))
  }} catch {{
    Write-Output ('ERR:' + $_.Exception.Message)
  }}
  [Console]::Out.Flush()
}}
"""


class CspSignSession:
    """Long-lived PowerShell CSP session — one vendor PIN for many file signatures."""

    def __init__(self, serial: str) -> None:
        self.serial = serial
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._start()

    @classmethod
    def get(cls, serial: str) -> "CspSignSession":
        key = (serial or "").upper().lstrip("0")
        with _LOCK:
            sess = _SESSIONS.get(key)
            if sess is not None and sess.alive:
                return sess
            sess = cls(serial)
            _SESSIONS[key] = sess
            return sess

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _start(self) -> None:
        script = _PS_SESSION_SCRIPT.format(serial=self.serial.replace("'", ""))
        self._proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            creationflags=0x08000000,
        )
        line = ""
        try:
            if self._proc.stdout is not None:
                line = self._proc.stdout.readline().strip()
        except Exception as e:  # noqa: BLE001
            raise TokenError(f"CSP session start failed: {e}", code="CSP_SIGN_FAILED") from e
        if line.startswith("ERR:") or line != "READY":
            self.close()
            raise TokenError(
                f"CSP session không mở được key CKS {self.serial}: {line or 'no READY'}",
                code="CSP_SIGN_FAILED",
            )

    def sign_digest(self, digest: bytes) -> bytes:
        with self._lock:
            if not self.alive or self._proc is None or self._proc.stdin is None:
                self._start()
            try:
                self._proc.stdin.write(base64.b64encode(digest).decode("ascii") + "\n")
                self._proc.stdin.flush()
                assert self._proc.stdout is not None
                line = self._proc.stdout.readline().strip()
            except Exception as e:  # noqa: BLE001
                self.close()
                raise TokenError(f"CSP session I/O failed: {e}", code="CSP_SIGN_FAILED") from e
        if line.startswith("OK:"):
            return base64.b64decode(line[3:])
        self.close()
        raise TokenError(f"CSP session ký thất bại: {line}", code="CSP_SIGN_FAILED")

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.write("QUIT\n")
                proc.stdin.flush()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def clear_csp_cache() -> None:
    """Reset CKS / switch token: close CSP sessions so next pick asks vendor PIN again."""
    with _LOCK:
        for s in list(_SESSIONS.values()):
            s.close()
        _SESSIONS.clear()


def load_store_der_by_serial(serial: str) -> bytes | None:
    if not serial or not sys.platform.startswith("win"):
        return None
    s = serial.replace("'", "").replace(" ", "")
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
    try:
        return base64.b64decode("".join(text.split()))
    except Exception:  # noqa: BLE001
        return None


def _hash_data(data: bytes, digest_algorithm: str) -> bytes:
    import hashlib

    name = (digest_algorithm or "sha256").lower().replace("-", "")
    if name not in ("md5", "sha1", "sha256", "sha384", "sha512"):
        name = "sha256"
    return hashlib.new(name, data).digest()


def csp_sign_digest(digest: bytes, serial: str) -> bytes:
    """Sign one digest; session reused for subsequent files in the same batch."""
    if not sys.platform.startswith("win"):
        raise TokenError("Windows CSP chỉ hỗ trợ trên Windows", code="CSP_UNSUPPORTED")
    return CspSignSession.get(serial).sign_digest(digest)


class WindowsCspSigner(_PyHankoSignerBase):
    """pyHanko Signer for Windows store certs — vendor PIN once per session."""

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
        return csp_sign_digest(self._to_digest(data, digest_algorithm), self._gs_serial)

    def sign_raw(
        self, data: bytes, digest_algorithm: str = "sha256", dry_run: bool = False
    ) -> bytes:
        if dry_run:
            return self.estimate_raw_signature_size_bytes() * b"\x00"
        return csp_sign_digest(self._to_digest(data, digest_algorithm), self._gs_serial)
