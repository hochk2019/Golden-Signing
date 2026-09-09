# ARCHITECTURE DECISION RECORD — Golden Signing Phase 0

Date: 2026-09-09
Status: Accepted (Phase 0)
Spec: Golden Signing 1.2.0 §1, §6, §7, §42, §58

## Context

Windows desktop app to digitally sign PDF documents for customs (PUS) workflows. Must preserve page content, support batch signing, USB tokens, post-sign verification, and remain maintainable by a small developer (HOC HK). Greenfield repository.

## Decisions

### ADR-1 — Language: Python 3.13

- Matches developer environment and PDF/signing ecosystem (pyHanko).
- pyHanko 0.37.0 requires Python >=3.10 and supports 3.13.
- Alternative rejected: .NET (no stack already proven on this machine; would delay Phase 1).

### ADR-2 — PDF signing engine: pyHanko 0.37.0 (MIT)

- Handles signature fields, ByteRange, CMS, PAdES, PKCS#11, validation, timestamps, interrupted signing.
- Golden Signing adds adapters, profiles, orchestration — does not reimplement PDF crypto.
- Install extras: pkcs11, image-support, opentype, qr, etsi as needed per phase.
- CLI is separate package pyhanko-cli (not bundled) — library use only in-app.

### ADR-3 — UI: PySide6 (Qt for Python)

- Spec-locked. Community Edition LGPLv3/GPLv3.
- Gate: before commercial closed-source distribution, produce THIRD_PARTY_LICENSES.md and confirm LGPL compliance (dynamic linking of unmodified Qt) or purchase Qt commercial license.
- Phase 0 does not import Qt in Signing Core.

### ADR-4 — PDF rendering preview: pypdfium2

- Already installed (4.30.1). Apache-2.0/BSD-3-Clause wrapper; ship PDFium third-party licenses with binaries.
- Do not use PyMuPDF in MVP (license model risk per spec §26).

### ADR-5 — Layering

```
UI (PySide6)
  -> Application services (orchestrator, batch)
    -> Domain contracts (Protocols, profiles, errors)
      -> Infrastructure adapters (pyHanko, PKCS#11, WinCrypto, SQLite)
```

- Signing Core must not import UI.
- UI must not call PKCS#11 directly.
- Database must not hold cryptographic business logic.

### ADR-6 — Storage: SQLite + migrations

- Local single-user desktop; no server DB.
- Tables per spec §46.3; schema_migrations versioning.
- Never store PIN, private keys, or token passwords.

### ADR-7 — Packaging: uv + PyInstaller onedir

- uv for lockfile-frozen, reproducible envs.
- PyInstaller onedir first (easier diagnostics); onefile later for portable dist.
- Code-sign EXE/DLL/installer before production release.

### ADR-8 — Signing profiles

- PUS-Compatibility vs Modern-PAdES as data profiles, not hard-coded.
- Certificate-linked profiles keyed by SHA-256 fingerprint (spec §44.2).
- verify_after_sign always true for PUS Safe.

### ADR-9 — Output safety

- Never overwrite source by default.
- Atomic write: temp -> verify -> fsync -> rename.
- No SUCCESS without Definition of Done checklist (spec §38).

## Consequences

- Phase 1 can prototype signing with a software/test certificate before USB token work.
- Commercial distribution blocked on license report.
- Agents must read .ai/START_HERE.md before code changes.
