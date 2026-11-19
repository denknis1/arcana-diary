"""The token check alone (spec 4.3 §3, §12): a local ES256 key, a fake key source, a fake monotonic clock."""
import uuid
from types import SimpleNamespace

import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm, has_crypto

from app.auth import AuthError, AuthUnavailable, KeySet, TokenVerifier, User, bearer_token, current_user
from helpers import AUTH_URL, OTHER_KEY, TEST_KEY, FakeJwks, jwk, jwks, make_token

USER = uuid.UUID("7d3f5c1e-9a1b-4c2d-8e3f-1a2b3c4d5e6f")


class Monotonic:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def verifier(source=None, clock=None):
    source = source or FakeJwks()
    return TokenVerifier(AUTH_URL, keys=KeySet(source, monotonic=clock or Monotonic())), source


def request(authorization: str | None):
    return SimpleNamespace(headers={} if authorization is None else {"authorization": authorization})


def test_es256_is_available():
    assert has_crypto


def test_a_valid_token_gives_the_account():
    v, source = verifier()
    assert v.issuer == "https://test-project.supabase.co/auth/v1"
    assert v.verify(make_token(USER, email="Person@Example.COM")) == User(USER, "person@example.com")
    assert v.verify(make_token(USER, email=None)) == User(USER, None)
    assert v.verify(make_token(USER, iat=int(time.time()) + 30)).id == USER  # a little clock drift is fine
    assert source.calls == 1


@pytest.mark.parametrize("token", [
    make_token(USER, expires_in=-120),
    make_token(USER, key=OTHER_KEY),
    make_token(USER, aud="anon"),
    make_token(USER, iss="https://other-project.supabase.co/auth/v1"),
    make_token("not-a-uuid"),
    make_token(USER, key="a-shared-secret-that-is-long-enough-for-hs256", alg="HS256"),
    make_token(USER, is_anonymous=True),
    "not.a.token",
    "",
], ids=["expired", "other-signature", "wrong-aud", "wrong-iss", "bad-sub", "hs256", "anonymous", "garbage", "empty"])
def test_bad_tokens_are_auth_errors(token):
    v, _ = verifier()
    with pytest.raises(AuthError):
        v.verify(token)


def test_a_token_without_a_kid_never_reaches_the_keys():
    v, source = verifier()
    with pytest.raises(AuthError):
        v.verify(make_token(USER, kid=None))
    assert source.calls == 0


def test_a_kid_of_a_key_that_is_not_ec_is_an_auth_error():
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_jwk = {**RSAAlgorithm.to_jwk(rsa_key.public_key(), as_dict=True), "kid": "rsa-1", "alg": "RS256", "use": "sig"}
    v, _ = verifier(FakeJwks(jwks(jwk(TEST_KEY), rsa_jwk)))
    with pytest.raises(AuthError):  # an ES256 token naming an RSA key: 401, never a 500
        v.verify(make_token(USER, kid="rsa-1"))


def test_keys_are_cached_for_ten_minutes():
    clock = Monotonic()
    v, source = verifier(clock=clock)
    v.verify(make_token(USER))
    v.verify(make_token(USER))
    clock.t += 599
    v.verify(make_token(USER))
    assert source.calls == 1
    clock.t += 2
    v.verify(make_token(USER))
    assert source.calls == 2


def test_an_unknown_kid_fetches_the_keys_again():
    clock = Monotonic()
    v, source = verifier(clock=clock)
    v.verify(make_token(USER))
    source.keyset = jwks(jwk(TEST_KEY), jwk(OTHER_KEY, "rotated-2"))  # Supabase rotated its signing key
    clock.t += 31
    assert v.verify(make_token(USER, key=OTHER_KEY, kid="rotated-2")).id == USER
    assert source.calls == 2


def test_unknown_kids_do_not_hammer_the_key_source():
    clock = Monotonic()
    v, source = verifier(clock=clock)
    v.verify(make_token(USER))
    for _ in range(3):
        with pytest.raises(AuthError):
            v.verify(make_token(USER, kid="nobody"))
    assert source.calls == 1  # at most one fetch per 30 s
    clock.t += 31
    with pytest.raises(AuthError):
        v.verify(make_token(USER, kid="nobody"))
    assert source.calls == 2


def test_unreachable_keys_are_unavailable():
    v, source = verifier(FakeJwks(fail=True))
    with pytest.raises(AuthUnavailable):
        v.verify(make_token(USER))
    with pytest.raises(AuthUnavailable):  # no new fetch within 30 s
        v.verify(make_token(USER))
    assert source.calls == 1


def test_cached_keys_outlive_a_failed_refresh():
    clock = Monotonic()
    v, source = verifier(clock=clock)
    v.verify(make_token(USER))
    source.fail = True
    clock.t += 601
    assert v.verify(make_token(USER)).id == USER
    assert source.calls == 2
    with pytest.raises(AuthUnavailable):  # a new kid cannot be checked while the keys are unreachable
        v.verify(make_token(USER, kid="rotated-2"))


@pytest.mark.parametrize("header, expected", [
    (None, None), ("Basic YXJjYW5hOnNlY3JldA==", None), ("Bearer abc", "abc"), ("bearer  abc ", "abc"),
    ("Bearer", ""),
])
def test_bearer_token(header, expected):
    assert bearer_token(request(header)) == expected


def test_current_user():
    v, _ = verifier()
    assert current_user(v, request(None)) is None
    assert current_user(v, request("Basic YXJjYW5hOnNlY3JldA==")) is None  # the stage password: still a guest
    assert current_user(v, request(f"Bearer {make_token(USER)}")).id == USER
    with pytest.raises(AuthError):
        current_user(v, request("Bearer "))
    with pytest.raises(AuthError):  # SUPABASE_URL empty: sign-in is off, every token is refused
        current_user(None, request(f"Bearer {make_token(USER)}"))
    assert current_user(None, request(None)) is None
