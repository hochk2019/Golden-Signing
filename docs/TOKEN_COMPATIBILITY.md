# TOKEN COMPATIBILITY — Golden Signing

## Backend priority

1. **PKCS#11 native DLL** — primary. Discover library paths, enumerate slots/certs, login, sign digest.
2. **Windows Certificate Store / CSP / KSP** — fallback when token has no usable PKCS#11.
3. **Remote Signing / CSC** — future phase only.

## Rules (non-negotiable)

- Private key never leaves token; never export; never copy to temp.
- PIN only in memory for the minimum time; zeroize after use; never log.
- **Serialize** cryptographic operations per token (mutex). Parallelize only preflight/hash/render/verify pools.
- Token removal during signing: transition `SIGNING -> TOKEN_LOST -> WAITING_FOR_TOKEN`; do not crash app; do not mark SUCCESS.
- Reconnect: reopen session; re-enumerate certs; do not reuse dead handles.

## Discovery checklist (Phase 2)

Code support (unit-tested with Fake; Pkcs11Backend ready for hardware):

- [x] List PKCS#11 modules (vendor DLL, middleware path) — `token/discovery.py`
- [x] List slots with token present — `TokenBackend.list_slots` / Pkcs11Backend
- [x] List certificates with private key matching — Fake + Pkcs11Backend
- [x] Identify key algorithm/size — CertificateInfo fields
- [x] Login (prompt PIN only when required) — `TokenSessionManager` + `pin_provider`
- [x] Sign test digest — serialized `sign_digest`
- [x] Logout / close session — `close()`
- [x] Unplug / replug recovery test — Fake `simulate_unplug` + `recover()`

Hardware verification (user device required):

- [ ] Real DLL loads
- [ ] Real cert enumeration
- [ ] Real PIN login
- [ ] Real digest sign
- [ ] Physical unplug/replug

## Compatibility matrix (fill with real device)

| Token / CA | PKCS#11 DLL | Slot | Cert subject | Key | Backend | Notes |
|---|---|---|---|---|---|---|
| ECA Token v1.0 (ePass2003Auto) | `C:\Windows\System32\eca_csp11_v1.dll` | FT ePass2003Auto 0 | CÔNG TY TNHH JAEYOUNG VINA (MST:2300944637) | RSA (private key needs PIN) | pkcs11 | Detected 2026-09-09; wrong PIN → TokenError; full sign needs user PIN in UI |

## PUS note

ECUS sample uses SubFilter `adbe.pkcs7.sha1` with `/Filter /Adobe.PPKMS`. That is a **compatibility profile**, not a global mandate. Modern-PAdES remains available when the target system accepts it. Real PUS upload is the only acceptance for "PUS-compatible".
