# DEPENDENCY MATRIX — Golden Signing

Policy: pin versions in uv.lock; run pip-audit before every release; no runtime internet installs.

| Package | Purpose | License | Version (target) | Security status | Phase |
|---|---|---|---|---|---|
| Python | Runtime | PSF | 3.13.x | n/a | 0 |
| pyHanko | PDF signature engine | MIT | 0.37.0 | pin; audit at release | 1 |
| pyHanko extras pkcs11 | PKCS#11 token backend | MIT + python-pkcs11 deps | via pyHanko | audit | 2 |
| pypdfium2 | PDF preview render | Apache-2.0 / BSD-3-Clause (+ PDFium TP) | 4.30.1 installed | ship TP licenses | 5 |
| cryptography | Crypto primitives | Apache-2.0 OR BSD-3-Clause | >=43 | audit | 1 |
| PySide6 | Desktop UI | LGPLv3/GPLv3 or Qt commercial | pin at UI phase | license gate | 5 |
| httpx | Update checker HTTP | BSD-3-Clause | pin | TLS only; allowlist hosts | 8 |
| structlog | Structured logging | Apache-2.0 / MIT | pin | redaction required | 7 |
| pytest | Tests | MIT | pin | n/a | 1 |
| hypothesis | Property tests | MPL-2.0 | pin | n/a | 1 |
| mypy | Type check | MIT | pin | n/a | 0 |
| ruff | Lint/format | MIT | pin | n/a | 0 |
| pip-audit | Dependency audit | Apache-2.0 | pin | CI gate | 0/9 |
| PyInstaller | Windows packaging | GPL with exception / bootloader | pin | code-sign output | 9 |
| sqlite3 (stdlib) | Local DB | PSF | n/a | no secrets | 9 |

## Explicit non-dependencies (MVP)

- PyMuPDF (license risk)
- Electron / browser UI
- Cloud SDK / telemetry SDKs
- OCR stacks

## Install commands (uv)

```
uv sync
uv pip install 'pyHanko[pkcs11,image-support,opentype,qr,etsi]'
```

Exact pins live in `uv.lock` once generated.
