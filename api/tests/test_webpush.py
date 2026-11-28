"""Web Push by hand (stage 8.1, plan decision 1): RFC 8291 encryption against the RFC's own example, a browser-side
decryption of our messages, VAPID tokens, the push-host allowlist and the keys of a subscription."""
import json
import os
import struct

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import webpush
from app.webpush import b64url, b64url_decode

# RFC 8291 §5 (Push Message Encryption Example)
RFC = {
    "plaintext": b"When I grow up, I want to be a watermelon",
    "as_private": "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw",
    "ua_public": "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
    "auth": "BTBZMqHH6r4Tts7J_aSIgg",
    "salt": "DGv6ra1nlYgDCS1FRnbzlw",
    "body": "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3"
            "jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN",
}
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


def browser():
    """A browser's subscription keys: its private key (to read the message) and what it gives the site."""
    key = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    return key, b64url(webpush._point(key.public_key())), b64url(auth)


def decrypt(body: bytes, key: ec.EllipticCurvePrivateKey, auth: str) -> bytes:
    """What the browser does (RFC 8291 §3.4, from the receiving side)."""
    salt, rs, idlen = body[:16], *struct.unpack("!IB", body[16:21])
    as_public = body[21:21 + idlen]
    shared = key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public))
    ua_public = webpush._point(key.public_key())
    ikm = webpush._hkdf(b64url_decode(auth), shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    cek = webpush._hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = webpush._hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    padded = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert rs == webpush.RECORD_SIZE and padded.endswith(b"\x02")
    return padded[:-1]


def test_encryption_matches_the_example_of_rfc_8291():
    sender = ec.derive_private_key(int.from_bytes(b64url_decode(RFC["as_private"]), "big"), ec.SECP256R1())
    body = webpush.encrypt(RFC["plaintext"], RFC["ua_public"], RFC["auth"], sender=sender,
                           salt=b64url_decode(RFC["salt"]))
    assert b64url(body) == RFC["body"]


def test_a_browser_reads_our_message_and_every_message_differs():
    key, p256dh, auth = browser()
    first = webpush.encrypt(b'{"lang":"es"}', p256dh, auth)
    second = webpush.encrypt(b'{"lang":"es"}', p256dh, auth)
    assert decrypt(first, key, auth) == decrypt(second, key, auth) == b'{"lang":"es"}'
    assert first != second  # a fresh sender key and salt each time


def test_generated_keys_load_and_sign_a_vapid_token():
    private, public = webpush.generate_vapid()
    keys = webpush.load_vapid(private, public)
    assert keys is not None and keys.public_key == public and len(b64url_decode(public)) == 65
    header = webpush.vapid_authorization(ENDPOINT, keys, "https://arcanadiary.com", now=1_800_000_000)
    token = header.split("t=", 1)[1].split(",", 1)[0]
    assert header.endswith(f", k={public}")
    claims = jwt.decode(token, keys.private_key.public_key(), algorithms=["ES256"], audience="https://fcm.googleapis.com",
                        options={"verify_exp": False})
    assert claims == {"aud": "https://fcm.googleapis.com", "exp": 1_800_000_000 + 12 * 3600,
                      "sub": "https://arcanadiary.com"}


def test_missing_or_mismatched_keys_leave_reminders_off(caplog):
    private, public = webpush.generate_vapid()
    other_private, _ = webpush.generate_vapid()
    assert webpush.load_vapid("", "") is None
    with caplog.at_level("WARNING", logger="arcana.webpush"):
        assert webpush.load_vapid(other_private, public) is None
        assert webpush.load_vapid("not-a-key!", public) is None
        assert webpush.load_vapid(private, "") is None
    assert "does not belong" in caplog.text and "is not a P-256 key" in caplog.text
    assert private not in caplog.text  # never the key itself


@pytest.mark.parametrize("url, ok", [
    (ENDPOINT, True),
    ("https://updates.push.services.mozilla.com/wpush/v2/gAAAA", True),
    ("https://web.push.apple.com/QGuQyavXutnMH", True),
    ("https://wns2-db5p.notify.windows.com/w/?token=x", True),
    ("http://fcm.googleapis.com/fcm/send/abc", False),
    ("https://fcm.googleapis.com:8443/fcm/send/abc", False),
    ("https://user:pw@fcm.googleapis.com/fcm/send/abc", False),
    ("https://fcm.googleapis.com.evil.example/x", False),
    ("https://evilnotify.windows.com/x", False),
    ("https://169.254.169.254/latest/meta-data", False),
    ("https://localhost/x", False),
    ("https://fcm.googleapis.com", False),
    ("https://fcm.googleapis.com/" + "a" * 1100, False),
    ("https://[::1/x", False),
])
def test_only_known_push_services_are_accepted(url, ok):
    assert webpush.valid_endpoint(url) is ok


def test_subscription_keys_are_checked():
    _, p256dh, auth = browser()
    assert webpush.valid_keys(p256dh, auth)
    assert not webpush.valid_keys(p256dh, b64url(os.urandom(15)))
    assert not webpush.valid_keys(b64url(b"\x04" + bytes(64)), auth)  # not a point on the curve
    assert not webpush.valid_keys(p256dh[:-4], auth)
    assert not webpush.valid_keys("abc+/", auth)


def test_a_push_request_carries_the_vapid_header_and_a_readable_body():
    key, p256dh, auth = browser()
    keys = webpush.load_vapid(*webpush.generate_vapid())
    headers, body = webpush.push_request(ENDPOINT, p256dh, auth, {"lang": "en"}, keys, "https://arcanadiary.com",
                                         now=1_800_000_000)
    assert headers["Content-Encoding"] == "aes128gcm" and headers["TTL"] == "14400" and headers["Topic"] == "daily"
    assert headers["Authorization"].startswith("vapid t=")
    assert json.loads(decrypt(body, key, auth)) == {"lang": "en"}
