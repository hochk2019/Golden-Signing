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

- [ ] List PKCS#11 modules (vendor DLL, middleware path)
- [ ] List slots with token present
- [ ] List certificates with private key matching
- [ ] Identify key algorithm/size
- [ ] Login (prompt PIN only when required)
- [ ] Sign test digest
- [ ] Logout / close session
- [ ] Unplug / replug recovery test

## Compatibility matrix (fill during Phase 2)

| Token / CA | PKCS#11 DLL | Slot | Cert subject | Key | Backend | Notes |
|---|---|---|---|---|---|---|
| TBD | | | | | | user device |

## PUS note

ECUS sample uses SubFilter `adbe.pkcs7.sha1` with `/Filter /Adobe.PPKMS`. That is a **compatibility profile**, not a global mandate. Modern-PAdES remains available when the target system accepts it. Real PUS upload is the only acceptance for "PUS-compatible".
