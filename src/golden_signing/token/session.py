"""Token session manager — serialize crypto, PIN policy, token-lost recovery."""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from golden_signing.signing.contracts import CertificateInfo
from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.token.base import TokenBackend, TokenSessionState

if TYPE_CHECKING:
    from golden_signing.signing.contracts import SigningSession

__all__ = ["TokenSessionManager"]


class TokenSessionManager:
    """One manager instance = one token lane. All sign calls are serialized."""

    def __init__(
        self,
        backend: TokenBackend,
        *,
        pin_provider: Callable[[], str] | None = None,
        auto_login: bool = True,
    ) -> None:
        self._backend = backend
        self._pin_provider = pin_provider
        self._auto_login = auto_login
        self._lock = threading.RLock()
        self._state = TokenSessionState.CLOSED
        self._session: SigningSession | None = None
        self._login_attempts = 0

    @property
    def state(self) -> TokenSessionState:
        return self._state

    @property
    def backend(self) -> TokenBackend:
        return self._backend

    def list_certificates(self) -> Sequence[CertificateInfo]:
        with self._lock:
            try:
                return list(self._backend.list_certificates())
            except TokenLostError:
                self._state = TokenSessionState.TOKEN_LOST
                raise
            except TokenError:
                raise

    def open(self) -> None:
        with self._lock:
            if self._state is TokenSessionState.TOKEN_LOST:
                raise TokenLostError("token lost; call recover() first")
            if self._state in (TokenSessionState.OPEN, TokenSessionState.LOGGED_IN):
                return
            try:
                self._session = self._backend.open_session()
            except TokenLostError:
                self._state = TokenSessionState.TOKEN_LOST
                raise
            except TokenError:
                raise
            self._state = TokenSessionState.OPEN
            if self._auto_login:
                self._login_locked()

    def _login_locked(self) -> None:
        login = getattr(self._backend, "login", None)
        if login is None:
            # Backend does not require explicit login
            self._state = TokenSessionState.LOGGED_IN
            return
        if self._pin_provider is None:
            raise TokenError("PIN required but no pin_provider configured", code="PIN_REQUIRED")
        pin = self._pin_provider()
        # Do not retain PIN on the manager
        try:
            login(pin)
        except TokenLostError:
            self._state = TokenSessionState.TOKEN_LOST
            raise
        except TokenError as exc:
            self._login_attempts += 1
            code = getattr(exc, "code", None) or "TOKEN_ERROR"
            if code in ("WRONG_PIN", "PIN_CANCELLED"):
                raise
            raise
        finally:
            del pin
        self._state = TokenSessionState.LOGGED_IN

    def login(self) -> None:
        with self._lock:
            if self._state is TokenSessionState.TOKEN_LOST:
                raise TokenLostError("token lost; call recover() first")
            if self._state is TokenSessionState.CLOSED:
                self.open()
                return
            self._login_locked()

    def sign_digest(self, digest: bytes, algorithm: str = "sha256") -> bytes:
        """Sign a digest under the per-token mutex. Never parallel-safe without this lock."""
        with self._lock:
            if self._state is TokenSessionState.TOKEN_LOST:
                raise TokenLostError("token lost; call recover() before signing")
            if self._state is TokenSessionState.CLOSED:
                self.open()
            if self._state is not TokenSessionState.LOGGED_IN:
                raise TokenError("not logged in; call open()/login() first", code="TOKEN_ERROR")
            try:
                return self._backend.sign(digest, algorithm)
            except TokenLostError:
                self._state = TokenSessionState.TOKEN_LOST
                self._session = None
                raise
            except TokenError as exc:
                # Device-removed style errors mapped by backends as TokenLostError;
                # other TokenErrors stay as-is (wrong pin already handled at login).
                raise exc

    def health_check(self) -> bool:
        with self._lock:
            try:
                healthy = bool(self._backend.health_check())
            except Exception:  # noqa: BLE001
                healthy = False
            if not healthy:
                self._state = TokenSessionState.TOKEN_LOST
            return healthy

    def recover(self) -> TokenSessionState:
        """After unplug/replug: drop dead handles and reopen."""
        with self._lock:
            if self._session is not None:
                with contextlib.suppress(Exception):
                    self._session.close()
                self._session = None
            self._state = TokenSessionState.CLOSED
            try:
                self.open()
            except TokenLostError:
                self._state = TokenSessionState.TOKEN_LOST
            return self._state

    def close(self) -> None:
        with self._lock:
            if self._session is not None:
                with contextlib.suppress(Exception):
                    self._session.close()
                self._session = None
            self._state = TokenSessionState.CLOSED
