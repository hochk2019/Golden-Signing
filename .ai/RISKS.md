# RISKS

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R-01 | ECUS/PUS rejects pyHanko default profile | High | Medium | Dual profile: PUS-Compatibility + Modern-PAdES; golden structural compare |
| R-02 | USB token only exposes CSP/KSP (no PKCS#11) | High | Medium | Windows Crypto API adapter (Phase 2) |
| R-03 | PySide6 LGPL obligations missed for commercial ship | High | Medium | License gate before RC; document dynamic linking; consider Qt commercial |
| R-04 | Private fixtures leaked to public repo | High | Low | `.gitignore` + private/ README + no public remote |
| R-05 | Batch crash corrupts output | High | Medium | Atomic commit + post-sign verify + no SUCCESS without DoD checklist |
| R-06 | PIN/key leakage via logs | Critical | Low | Redaction layer; never log secrets; security tests |
| R-07 | `golden.svg` too heavy for UI/ICO pipeline | Low | High | Derive mark/PNG/ICO; keep source untouched |
| R-08 | Spec 1.2.0 vs 1.1.0 confusion for agents | Medium | High | REVISION_NOTE + START_HERE points to it |
| R-09 | Agent claims PUS ready without real upload | High | Medium | Status must be `TECHNICALLY READY / PUS REAL-WORLD VALIDATION PENDING` |
| R-10 | Antivirus false positive on PyInstaller onedir | Medium | Medium | Code signing; prefer onedir early; test clean machine |
