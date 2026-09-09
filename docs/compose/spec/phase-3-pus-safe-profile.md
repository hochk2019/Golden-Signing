---
feature: phase-3-pus-safe-profile
status: delivered
updated: 2026-09-09
branch: main
commits: 22231bb..a1d23a3 # Phase 3 delivery
---

# Phase 3 — PUS Safe Profile

## Report

**What was built** — `signing/pus_safe.py` with `EffectiveSigningSettings`, `resolve_signing_settings`, and hard `assert_pus_safe_invariants` (verify/preserve/atomic/incremental). `TestCertPdfSigner` resolves profile settings before sign and rejects invariant violations with `PROFILE_INVARIANT`. SubFilter intent is `profile-controlled` for PUS Safe (does **not** force ECUS `adbe.pkcs7.sha1`). Golden regression under `tests/regression/` proves fixture hashes stable, lab sign preserves source, output verifies, ByteRange valid, 4 pages.

**Verification** — full `pytest -q` exit 0; pus_safe unit + golden regression green; mypy/ruff clean.

**Journey log**
1. Forced verify_after_sign at resolve time even if profile object is tampered.
2. Kept packaging modern until real PUS upload proves compatibility profile.
3. Real PUS acceptance remains `PENDING` by design.

## [S1] Problem

Phase 1 lab-signs with defaults but does not enforce the PUS Safe profile contract from spec §5.4 / §12 / ADR-8: invisible default, incremental update, post-sign verification always on, preserve original content/geometry, profile-driven SubFilter (not hard-coded ECUS SHA-1). Production path needs a typed profile → engine mapping and golden-fixture regression that proves content preservation without claiming PUS acceptance.

## [S2] Design

### Workspace

Continue on `main` (prior consent). Commit only, no push.

### Profile contract (extend `SigningProfile` usage, not rewrite contracts)

`PusSafeOptions` / effective settings resolved from `SigningProfile` + `PusProfile`:

| Setting | PUS Safe | Modern PAdES |
|---|---|---|
| mode default | INVISIBLE | caller |
| verify_after_sign | **forced True** | default True |
| atomic_commit | True | True |
| preserve_original | True | True |
| incremental | True | True |
| subfilter intent | `profile-controlled` (record actual; do not force sha1) | modern detached |

Add `golden_signing/signing/pus_safe.py`:

- `resolve_signing_settings(profile: SigningProfile) -> EffectiveSigningSettings`
- `assert_pus_safe_invariants(settings)` — raises if verify_after_sign disabled for PUS_SAFE

Wire `TestCertPdfSigner.sign` to accept resolved settings (reason/location already optional). Ensure verify always runs when settings.verify_after_sign.

### Content preservation

Reuse Phase 1 `sha256_file` on source before/after; ByteRange validate on output. Golden test: sign `ecus_source.pdf` copy → source hash unchanged → output preflight WARN with ≥1 signature → verify crypto.

### Golden fixture regression (regression/)

`tests/regression/test_pus_safe_golden.py`:

1. Hash fixtures match START_HERE.
2. PUS Safe resolve → verify_after_sign True, mode invisible.
3. Sign source copy with test cert + PUS Safe settings.
4. Assert source untouched, output verifies, ByteRange valid.
5. Baseline page_count still 4.

### Out of Scope

- Real PUS upload / “PUS accepted” claim
- Visible appearance designer
- Token-backed signing (Phase 2 layer exists; PDF engine still lab cert)
- Batch UI
- Forcing `adbe.pkcs7.sha1`

## Tasks

- [x] T1: `pus_safe.py` EffectiveSigningSettings + resolve + invariants — unit tests (covers: S2)
- [x] T2: Wire pdf_signer to resolved settings; always verify when required — unit/integration (covers: S2; depends: T1)
- [x] T3: Golden regression suite `tests/regression/` — fixtures + sign + preserve (covers: S1; depends: T2)
- [x] T4: Review notes + control-plane + commit — tests green (covers: S2; depends: T1–T3)

## Acceptance criteria

1. `pytest` exit 0 including regression package.
2. PUS Safe cannot disable post-sign verify (invariant test).
3. Golden source SHA-256 unchanged after lab sign.
4. Output cryptographically verifies; ByteRange valid.
5. No PUS acceptance claim.
