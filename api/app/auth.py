"""Sign-in check (spec 2026-11-19 stage 4.3 §3). The browser signs in with Supabase (e-mail link, Google) and
sends `Authorization: Bearer <access token>`; the API checks the ES256 signature against the project's public keys
(JWKS), exp, aud = "authenticated" and iss = <SUPABASE_URL>/auth/v1. No password, no session, no auth cookie (so no
CSRF): the account is `sub`, the e-mail is `email`.

- No Authorization header, or another scheme (the stage password sends Basic through Caddy): a guest, as before.
- A bad, forged or expired token, a token without a kid and an anonymous Supabase session (`is_anonymous`):
  AuthError -> 401 {"reason": "auth"} (the browser refreshes the token and retries), never a silent switch to a
  guest. Sign-in off (SUPABASE_URL empty): every Bearer token is an AuthError.
- The keys cannot be fetched (and none are cached, or the token names a key we do not have):
  AuthUnavailable -> 503 {"reason": "auth_unavailable"}.

Keys are cached for KEYS_TTL_S; a token with an unknown kid fetches them again. Fetches are at most one per
REFETCH_MIN_S, so tokens with made-up kids cannot turn into a stream of requests to Supabase; when a refresh
fails, the cached keys stay in use.
"""
import logging
import threading
import time
import uuid
from dataclasses import dataclass

import httpx
import jwt

log = logging.getLogger("arcana.auth")

ALGORITHMS = ["ES256"]
AUDIENCE = "authenticated"
KEYS_TTL_S = 600.0
REFETCH_MIN_S = 30.0
FETCH_TIMEOUT_S = 5.0
LEEWAY_S = 60  # clock drift between Supabase and this server (PyJWT also refuses an iat in the future)


class AuthError(Exception):
    """401 {"reason": "auth"}."""


class AuthUnavailable(Exception):
    """503 {"reason": "auth_unavailable"}."""


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str | None


class HttpJwks:
    """GET <SUPABASE_URL>/auth/v1/.well-known/jwks.json (public keys, no API key needed)."""

    def __init__(self, url: str, timeout_s: float = FETCH_TIMEOUT_S):
        self.url = url
        self.timeout_s = timeout_s

    def __call__(self) -> dict:
        response = httpx.get(self.url, timeout=self.timeout_s)
        response.raise_for_status()
        return response.json()


class KeySet:
    """The project's signing keys by kid, from `fetch()` (a JWKS dict)."""

    def __init__(self, fetch, ttl_s: float = KEYS_TTL_S, refetch_min_s: float = REFETCH_MIN_S,
                 monotonic=time.monotonic):
        self._fetch = fetch
        self._ttl_s = ttl_s
        self._refetch_min_s = refetch_min_s
        self._monotonic = monotonic
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None
        self._tried_at: float | None = None
        self._failed = False
        self._lock = threading.Lock()

    def _refresh(self, now: float) -> None:
        self._tried_at = now
        try:
            keys = {key.key_id: key for key in jwt.PyJWKSet.from_dict(self._fetch()).keys if key.key_id}
        except Exception as exc:  # network, HTTP status, bad JSON, no usable key: keep what we have
            self._failed = True
            log.warning("sign-in keys could not be fetched: %s", exc)
            return
        self._keys, self._fetched_at, self._failed = keys, now, False

    def get(self, kid: str | None) -> jwt.PyJWK:
        with self._lock:
            now = self._monotonic()
            due = (self._fetched_at is None or now - self._fetched_at >= self._ttl_s
                   or kid not in self._keys)
            if due and (self._tried_at is None or now - self._tried_at >= self._refetch_min_s):
                self._refresh(now)
            key = self._keys.get(kid)
            failed = self._failed
        if key is None:
            if failed:
                raise AuthUnavailable("sign-in keys are unavailable")
            raise AuthError("unknown key id")
        return key


class TokenVerifier:
    def __init__(self, supabase_url: str, fetch=None, keys: KeySet | None = None):
        self.issuer = f"{supabase_url}/auth/v1"
        self.keys = keys or KeySet(fetch or HttpJwks(f"{self.issuer}/.well-known/jwks.json"))

    def verify(self, token: str) -> User:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError("malformed token") from exc
        if header.get("alg") not in ALGORITHMS:  # never HS256 or "none", whatever the token says
            raise AuthError("algorithm")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:  # names no key: no lookup, no refetch
            raise AuthError("no key id")
        key = self.keys.get(kid)
        try:
            claims = jwt.decode(token, key.key, algorithms=ALGORITHMS, audience=AUDIENCE, issuer=self.issuer,
                                leeway=LEEWAY_S, options={"require": ["exp", "sub", "aud", "iss"]})
            user_id = uuid.UUID(str(claims["sub"]))
        except (jwt.PyJWTError, ValueError, TypeError) as exc:  # TypeError: the kid names a key that is not EC
            raise AuthError(type(exc).__name__) from exc
        if claims.get("is_anonymous"):  # an anonymous Supabase session is not an account (stage 4.3 §3)
            raise AuthError("anonymous")
        email = claims.get("email")
        return User(user_id, email.strip().lower() if isinstance(email, str) and email.strip() else None)


def bearer_token(request) -> str | None:
    """The token of `Authorization: Bearer <token>` ("" when it is empty); None without the header or with
    another scheme."""
    value = (request.headers.get("authorization") or "").strip()
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip()


def current_user(verifier: TokenVerifier | None, request) -> User | None:
    token = bearer_token(request)
    if token is None:
        return None
    if verifier is None or not token:
        raise AuthError("sign-in is off" if verifier is None else "empty token")
    return verifier.verify(token)
