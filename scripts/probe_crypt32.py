from __future__ import annotations

import ctypes

print("voidp", ctypes.sizeof(ctypes.c_void_p))
try:
    import win32crypt32

    print("win32crypt32", [x for x in dir(win32crypt32) if "Cert" in x or "Crypt" in x][:50])
except Exception as e:  # noqa: BLE001
    print("win32crypt32 fail", e)

crypt32 = ctypes.WinDLL("crypt32.dll", use_last_error=True)
f = crypt32.CertOpenSystemStoreW
f.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
f.restype = ctypes.c_void_p
store = f(0, "My")
print("store", hex(store) if store else None)
if not store:
    raise SystemExit(1)

class CERT_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("dwCertEncodingType", ctypes.c_uint32),
        ("pbCertEncoded", ctypes.c_void_p),
        ("cbCertEncoded", ctypes.c_uint32),
        ("pCertInfo", ctypes.c_void_p),
        ("hCertStore", ctypes.c_void_p),
    ]

print("sizeof CERT_CONTEXT", ctypes.sizeof(CERT_CONTEXT))
enum = crypt32.CertEnumCertificatesInStore
enum.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
enum.restype = ctypes.POINTER(CERT_CONTEXT)
prop = crypt32.CertGetCertificateContextProperty
prop.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
prop.restype = ctypes.c_int
free = crypt32.CertFreeCertificateContext
free.argtypes = [ctypes.c_void_p]
free.restype = ctypes.c_int
close = crypt32.CertCloseStore
close.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

prev = None
n = 0
while True:
    ctx = enum(store, prev)
    if not ctx:
        break
    prev = ctx
    try:
        c = ctx.contents
        der_len = c.cbCertEncoded
        der_ptr = c.pbCertEncoded
        print(f"cert#{n} enc={c.dwCertEncodingType} len={der_len} ptr={der_ptr}")
        if der_ptr and 0 < der_len < 100000:
            der = ctypes.string_at(der_ptr, der_len)
            print("  der head", der[:8].hex(), "len", len(der))
        cb = ctypes.c_uint32(0)
        ok = prop(ctx, 2, None, ctypes.byref(cb))
        print("  key_prov_info", bool(ok), "cb", cb.value)
        n += 1
        if n >= 8:
            # still must free current; break after
            free(ctx)
            break
    finally:
        if n < 8:
            free(ctx)
close(store, 0)
print("done certs_seen", n)
