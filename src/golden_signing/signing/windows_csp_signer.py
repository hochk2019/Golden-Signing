"""Windows CSP signing — vendor PIN dialog; one key context per process/batch."""

from __future__ import annotations

import ctypes
import hashlib
import sys
from ctypes import wintypes
from typing import Any

from golden_signing.signing.exceptions import TokenError
from pyhanko.sign.signers import Signer as _PyHankoSignerBase

__all__ = ["WindowsCspSigner", "csp_sign_digest", "load_store_der_by_serial", "clear_csp_cache"]

_DIGEST_SIZES = {16, 20, 32, 48, 64}

# Process-wide CryptoAPI handles so batch signing does not re-prompt PIN per file
_CSP_PROV: dict[str, Any] = {}  # serial_norm -> {"hprov": int, "keyspec": int}


def clear_csp_cache() -> None:
    _CSP_PROV.clear()


def _norm_serial(serial: str) -> str:
    return (serial or "").replace(" ", "").upper().lstrip("0")


def load_store_der_by_serial(serial: str) -> bytes | None:
    if not serial or not sys.platform.startswith("win"):
        return None
    import base64
    import subprocess

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
    name = (digest_algorithm or "sha256").lower().replace("-", "")
    if name not in ("md5", "sha1", "sha256", "sha384", "sha512"):
        name = "sha256"
    return hashlib.new(name, data).digest()


def _csp_sign_silent(digest: bytes, serial: str) -> bytes | None:
    """In-process CryptSignHash; reuse provider so vendor PIN prompts once per token unlock."""
    if not sys.platform.startswith("win"):
        return None
    key = _norm_serial(serial)
    crypt32 = ctypes.WinDLL("crypt32.dll", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32.dll", use_last_error=True)

    CertOpenSystemStoreW = crypt32.CertOpenSystemStoreW
    CertOpenSystemStoreW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    CertOpenSystemStoreW.restype = ctypes.c_void_p
    CertEnumCertificatesInStore = crypt32.CertEnumCertificatesInStore
    CertEnumCertificatesInStore.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    CertEnumCertificatesInStore.restype = ctypes.c_void_p
    CertFreeCertificateContext = crypt32.CertFreeCertificateContext
    CertFreeCertificateContext.argtypes = [ctypes.c_void_p]
    CertCloseStore = crypt32.CertCloseStore
    CertCloseStore.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    CryptAcquireCertificatePrivateKey = crypt32.CryptAcquireCertificatePrivateKey
    CryptAcquireCertificatePrivateKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_int),
    ]
    CryptAcquireCertificatePrivateKey.restype = ctypes.c_int
    CryptCreateHash = advapi.CryptCreateHash
    CryptCreateHash.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    CryptSetHashParam = advapi.CryptSetHashParam
    CryptSetHashParam.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
    CryptSignHashW = advapi.CryptSignHashW
    CryptSignHashW.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    CryptDestroyHash = advapi.CryptDestroyHash
    CryptDestroyHash.argtypes = [ctypes.c_void_p]

    CALG_SHA_256 = 0x800C
    HP_HASHVAL = 2
    CERT_ACQUIRE_SILENT_KEY = 0x40
    PROV_RSA_AES = 24

    cache = _CSP_PROV.get(key)
    if cache:
        hprov, keyspec = cache["hprov"], cache["keyspec"]
        hhash = ctypes.c_void_p()
        if CryptCreateHash(hprov, CALG_SHA_256, None, 0, ctypes.byref(hhash)):
            try:
                buf = ctypes.create_string_buffer(digest)
                if not CryptSetHashParam(hhash, HP_HASHVAL, buf, 0):
                    return None
                n = ctypes.c_uint32(0)
                if not CryptSignHashW(ctypes.byref(hhash), keyspec, None, 0, None, ctypes.byref(n)):
                    return None
                out = ctypes.create_string_buffer(n.value)
                if not CryptSignHashW(
                    ctypes.byref(hhash), keyspec, None, 0, out, ctypes.byref(n)
                ):
                    return None
                return out.raw[: n.value]
            finally:
                CryptDestroyHash(hhash)
        return None

    # First call: find cert, acquire private key (may show vendor PIN once)
    store = CertOpenSystemStoreW(None, "My")
    if not store:
        return None
    hprov = ctypes.c_void_p()
    keyspec = ctypes.c_uint32(0)
    found = False
    prev = None
    try:
        while True:
            ctx = CertEnumCertificatesInStore(store, prev)
            if not ctx:
                break
            prev = ctx
            # read serial from cert via cryptography on DER — need DER from context
            # CERT_CONTEXT layout: dwEnc, pbCertEncoded ptr, cbCertEncoded
            class _CC(ctypes.Structure):
                _fields_ = [
                    ("dw", ctypes.c_uint32),
                    ("pb", ctypes.POINTER(ctypes.c_ubyte)),
                    ("cb", ctypes.c_uint32),
                    ("info", ctypes.c_void_p),
                    ("hs", ctypes.c_void_p),
                ]

            c = ctypes.cast(ctx, ctypes.POINTER(_CC)).contents
            if c.pb and 0 < c.cb < 20000:
                der = ctypes.string_at(c.pb, c.cb)
                try:
                    from cryptography import x509

                    cert = x509.load_der_x509_certificate(der)
                    sn = format(cert.serial_number, "X").upper().lstrip("0")
                    if sn != key:
                        continue
                except Exception:  # noqa: BLE001
                    continue
                free = ctypes.c_int(0)
                if CryptAcquireCertificatePrivateKey(
                    ctx,
                    CERT_ACQUIRE_SILENT_KEY,
                    None,
                    ctypes.byref(hprov),
                    ctypes.byref(keyspec),
                    ctypes.byref(free),
                ):
                    found = True
                    break
                # retry without SILENT — vendor PIN dialog
                if CryptAcquireCertificatePrivateKey(
                    ctx, 0, None, ctypes.byref(hprov), ctypes.byref(keyspec), ctypes.byref(free)
                ):
                    found = True
                    break
    finally:
        CertCloseStore(store, 0)

    if not found or not hprov:
        return None
    _CSP_PROV[key] = {"hprov": hprov, "keyspec": keyspec.value}
    return _csp_sign_silent(digest, serial)


def _csp_sign_dotnet(digest: bytes, serial: str) -> bytes:
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
  $sn = $c.SerialNumber.ToUpperInvariant() -replace '^0+',''
  $want = '{serial}'.ToUpperInvariant() -replace '^0+',''
  if($sn -eq $want) {{ $cert = $c; break }}
}}
$store.Close()
if($cert -eq $null) {{ Write-Output 'ERR:NO_CERT'; exit 1 }}
$rsa = $null
try {{ $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert) }} catch {{ $rsa = $null }}
if($null -eq $rsa) {{ try {{ $rsa = $cert.PrivateKey }} catch {{ $rsa = $null }} }}
if($null -eq $rsa) {{ Write-Output 'ERR:NO_RSA'; exit 1 }}
try {{
  $sig = $rsa.SignHash($digest, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
  [IO.File]::WriteAllBytes('{out_win}', $sig)
  Write-Output ('OK:' + $sig.Length)
}} catch {{
  Write-Output ('ERR:' + $_.Exception.Message)
}}
"""
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            creationflags=0x08000000,
        )
        out = (proc.stdout or "").strip()
        if not out.startswith("OK:") or not outp.is_file():
            raise TokenError(
                f"CSP không ký được serial {serial}: {out or (proc.stderr or '')[:180]}",
                code="CSP_SIGN_FAILED",
            )
        return outp.read_bytes()


def csp_sign_digest(digest: bytes, serial: str) -> bytes:
    """Sign digest via Windows CSP; prefer silent/reused provider (one PIN per unlock)."""
    if not sys.platform.startswith("win"):
        raise TokenError("Windows CSP chỉ hỗ trợ trên Windows", code="CSP_UNSUPPORTED")
    if not load_store_der_by_serial(serial):
        raise TokenError(
            f"Không tìm thấy CKS serial {serial} trong Windows cert store.",
            code="CSP_CERT_MISSING",
        )
    sig = None
    try:
        sig = _csp_sign_silent(digest, serial)
    except Exception:  # noqa: BLE001
        sig = None
    if sig:
        return sig
    # Fallback: .NET SignHash (may show vendor PIN dialog once)
    sig = _csp_sign_dotnet(digest, serial)
    # Try cache provider for next files in batch
    try:
        _csp_sign_silent(digest, serial)
    except Exception:  # noqa: BLE001
        pass
    return sig


class WindowsCspSigner(_PyHankoSignerBase):
    """pyHanko Signer for Windows store certs (vendor PIN UI, no app PIN dialog)."""

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
