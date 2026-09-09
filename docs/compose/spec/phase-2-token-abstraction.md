---
feature: phase-2-token-abstraction
status: delivered
updated: 2026-09-09
branch: main
commits: 7b6acb3..HEAD # Phase 2 delivery
---

# Phase 2 — Token Abstraction

## Report

**What was built** — A complete token abstraction layer: `TokenBackend` Protocol + `TokenSessionState`, Windows PKCS#11 DLL discovery (env `GOLDEN_SIGNING_PKCS11` first, never loads libraries), `TokenSessionManager` with per-token `RLock` serialization, PIN via callable provider (not retained), `TOKEN_LOST` / `recover()` after unplug/replug, `Pkcs11Backend` over python-pkcs11 (missing DLL → `TokenError`, device-removed → `TokenLostError`), and `FakeTokenBackend` for CI. Sign path refuses non-logged-in state with `TokenError` (no bare assert).

**Verification** — `pytest -q` exit 0 (full suite + 23 token tests); `mypy` token modules exit 0; `ruff` token modules exit 0; concurrent sign 8/8 serialized; unplug/replug recovery green.

**Journey log**
1. Independent review subagent hit APIError; review completed in-session (`.ai/reviews/phase2-token.md`).
2. Replaced `assert LOGGED_IN` with explicit `TokenError` after review.
3. Real hardware token still not tested — matrix in TOKEN_COMPATIBILITY remains TBD.
4. python-pkcs11 is installed; pyHanko PKCS#11 signer not used in this phase (digest sign at token layer only).

## [S1] Problem

Phase 1 signs only with an ephemeral software certificate. Production Golden Signing must discover USB token PKCS#11 modules, enumerate slots/certificates, login with PIN (only when required), sign digests **serialized per token**, and survive unplug/replug without crashing the app. Spec §30 Phase 2 and TOKEN_COMPATIBILITY discovery checklist require this layer before batch/UI work.

Without it, there is no path from lab signing to real Vietnamese CA tokens (NACENCOMM, etc.).

## [S2] Design

### Workspace

Continue on `main` at `E:\GPT\Golden Signing` (prior explicit user consent for this project).

### Skills

compose-next process; TDD; systematic-debugging; verification-before-completion; independent review subagent.

### Architecture

```
UI / batch (later)
  -> TokenSessionManager  (mutex, state machine, PIN policy)
    -> TokenBackend Protocol
      -> Pkcs11Backend (python-pkcs11 + vendor DLL)
      -> FakeTokenBackend (tests only)
```

- Signing Core / PDF engine never load PKCS#11 directly.
- UI (future) never calls PKCS#11 directly.
- Private key never leaves the token.
- PIN never logged, never persisted, zeroized after use where feasible.

### Module layout

```
src/golden_signing/token/
  __init__.py
  base.py          # TokenSlotInfo, TokenBackend Protocol, session states
  discovery.py     # Windows PKCS#11 DLL discovery
  session.py       # TokenSessionManager — serialize, reconnect, token-lost
  pkcs11.py        # Pkcs11Backend using python-pkcs11
tests/
  unit/test_token_discovery.py
  unit/test_token_session.py
  unit/test_token_pkcs11_fake.py
  integration/test_token_fake_sign.py
```

### Contracts (token/base.py)

```python
class TokenSessionState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    LOGGED_IN = "logged_in"
    TOKEN_LOST = "token_lost"

@dataclass(frozen=True, slots=True)
class TokenSlotInfo:
    slot_id: int
    label: str
    token_present: bool
    token_label: str | None = None
    manufacturer: str | None = None

class TokenBackend(Protocol):
    def list_slots(self) -> Sequence[TokenSlotInfo]: ...
    def list_certificates(self) -> Sequence[CertificateInfo]: ...
    def open_session(self) -> SigningSession: ...
    def sign(self, digest: bytes, algorithm: str) -> bytes: ...
    def health_check(self) -> bool: ...
```

`SignerBackend` from `signing.contracts` remains the PDF-facing Protocol; `TokenBackend` extends the operational surface (slots/health).

### Discovery (discovery.py)

Search order:

1. `GOLDEN_SIGNING_PKCS11` env var (path or path-list separated by `;`)
2. Well-known Windows paths (OpenSC, vendor middleware under `Program Files`, `System32`)
3. Optional extra roots passed by caller

Return existing files only. Never load during discovery. Unknown DLLs are candidates, not trusted — load is explicit and failures surface as `TOKEN_ERROR`.

### Session manager (session.py)

- `threading.Lock` serializes all crypto on one manager instance (one token lane).
- `sign_digest(digest, algorithm)`:
  1. acquire lock
  2. if state is `TOKEN_LOST` → raise `TokenLostError`
  3. if not logged in → login (PIN from callable provider, not stored)
  4. call backend.sign
  5. on `DeviceRemoved`/`TokenError` device-lost → state=`TOKEN_LOST`, raise `TokenLostError`
  6. release lock in `finally`
- `recover()`: close dead session, reopen, re-enumerate, state=`OPEN` or `LOGGED_IN`
- PIN provider: `Callable[[], str]` invoked only when login required; manager does not keep PIN after login returns.
- `health_check()` backend call without forcing login when possible.

### Pkcs11Backend (pkcs11.py)

- Construct with `library_path: Path` and optional `token_label` / slot filter.
- Load via `pkcs11.lib(str(path))`.
- Enumerate slots with token present; map to `TokenSlotInfo`.
- Enumerate X.509 certs + matching private keys → `CertificateInfo` (subject, issuer, serial, SHA-256 fingerprint, key algorithm/size, token label, backend=`pkcs11`).
- `sign(digest, algorithm)`: find private key, `key.sign(digest, mechanism=...)` — mechanism mapped from algorithm name (`sha256` → `Mechanism.SHA256_RSA_PKCS` or CKM as supported).
- Missing library / no token → raise `TokenError`, never crash process.

### FakeTokenBackend (tests)

- In-memory RSA-2048; implements full `TokenBackend`.
- `simulate_unplug()` → subsequent sign raises device-removed → manager maps to `Token_LOST`.
- `simulate_replug()` restores.

### Concurrency

- One manager = one token lane. Do not call `sign` from multiple threads without the manager lock.
- Preflight/hash/verify pools stay outside this module.

### Out of Scope

- Windows CSP/KSP adapter (fallback later if token has no PKCS#11)
- Remote/CSC signing
- Multi-token lanes UI
- PIN UI dialog (provider injection only)
- Real hardware token in CI (user device for compatibility matrix)
- PDF signing orchestration changes beyond accepting `SignerBackend`

## Tasks

- [x] T1: `token/base.py` types + Protocol — acceptance: import clean; unit test state enum (covers: S2)
- [x] T2: `discovery.py` + unit tests — acceptance: env override wins; missing path filtered; no DLL load (covers: S2)
- [x] T3: FakeTokenBackend + tests — acceptance: list certs, sign digest, simulate unplug (covers: S2)
- [x] T4: TokenSessionManager serialize/login/lost/recover — acceptance: concurrent sign serialized; unplug → TokenLostError + state TOKEN_LOST; recover restores; PIN not retained (covers: S2; depends: T1, T3)
- [x] T5: Pkcs11Backend shell — acceptance: missing DLL raises TokenError; API surface complete; real-token path documented (covers: S2; depends: T1)
- [x] T6: Integration fake sign digest — acceptance: manager.sign returns verifiable RSA signature over digest (covers: S1; depends: T3, T4)
- [x] T7: Independent review + control-plane + commit — acceptance: review notes; PROJECT_STATE/NEXT_ACTION updated; tests green (covers: S2; depends: T1–T6)

## Acceptance criteria (phase)

1. `pytest` exit 0 including new token tests.
2. Discovery does not load libraries; env `GOLDEN_SIGNING_PKCS11` respected.
3. Session manager never allows parallel `sign` on one instance.
4. Unplugged fake token → `TokenLostError`, state `TOKEN_LOST`, no process crash.
5. `recover()` returns to usable state after replug.
6. No PIN/private key in logs or files.
7. No claim of real-token or PUS compatibility.
