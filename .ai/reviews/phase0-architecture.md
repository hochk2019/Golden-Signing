# Phase 0 Architecture self-review

Reviewer: orchestrator (same session — independent multi-role review deferred to Phase 1 gate per spec §48 scale).

## Questions (spec §28 Review A)

1. **Module that signs?** `golden_signing.signing` (contracts) + future `pdf_signer` / `cms_builder` adapters wrapping pyHanko. Not UI.
2. **Private key leave token?** No — contracts expose `sign(digest)` only; no key export APIs.
3. **UI call PKCS#11?** Forbidden by ADR-5; token isolated under `token/`.
4. **Batch serialize signing?** Spec §8.1; state machine present; lanes Phase 4.
5. **PDF rewrite?** Not in Phase 0; atomic helpers only.
6. **Verify before commit?** `SigningProfile.verify_after_sign` default True; PUS Safe locks it on later.

## Result

**PASS (Phase 0 scope)** — foundation matches ADR and safety rules.

## Open for Phase 1

- Implement preflight against golden fixtures.
- Sign with software certificate + structural compare to ECUS baseline.
- Independent PDF/PKI review artifact.
