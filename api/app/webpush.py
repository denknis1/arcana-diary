"""Web Push without a new package (stage 8.1 §4, plan decision 1): the message encryption of RFC 8291
(aes128gcm content coding, RFC 8188) and VAPID (RFC 8292), built on `cryptography` and PyJWT, which the API already
pins for sign-in (ES256 tokens). The test vector of RFC 8291 §5 checks the encryption byte for byte.

- VapidKeys: the server's P-256 key from VAPID_PRIVATE_KEY (32 bytes, base64url) and VAPID_PUBLIC_KEY (the
  65-byte uncompressed point, base64url; the browser takes it as applicationServerKey). Missing, malformed or not a
  pair: None, a line in the log, and browser reminders stay off — the API itself keeps working.
- valid_endpoint: only https addresses of the known push services, so a stored subscription can never make the
  server send requests anywhere else (SSRF).
- push_request: the headers and the encrypted body of one message; the caller sends it.
"""
import base64
import binascii
import hashlib
import json
import logging
import os
import re
import struct
from dataclasses import dataclass
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger("arcana.webpush")

RECORD_SIZE = 4096
VAPID_TTL_S = 12 * 3600       # RFC 8292: at most 24 hours
PUSH_TTL_S = 4 * 3600         # a phone that is off for longer gets no stale "your card is waiting"
ENDPOINT_MAX = 1024
PUSH_HOSTS = frozenset({"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"})
PUSH_HOST_SUFFIXES = (".notify.windows.com", ".push.apple.com")
_B64URL = re.compile(r"[A-Za-z0-9_-]+={0,2}")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """Strict base64url (the alphabet of RFC 4648 §5, padding optional); ValueError otherwise."""
    if not isinstance(text, str) or not _B64URL.fullmatch(text):
        raise ValueError("not base64url")
    try:
        return base64.urlsafe_b64decode(text.rstrip("=") + "=" * (-len(text.rstrip("=")) % 4))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("not base64url") from exc


def _point(public_key: ec.EllipticCurvePublicKey) -> bytes:
    return public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


@dataclass(frozen=True)
class VapidKeys:
    private_key: ec.EllipticCurvePrivateKey
    public_key: str


def generate_vapid() -> tuple[str, str]:
    """A new key pair (private, public) as deploy/gen-vapid.sh writes them into deploy/.env."""
    key = ec.generate_private_key(ec.SECP256R1())
    return b64url(key.private_numbers().private_value.to_bytes(32, "big")), b64url(_point(key.public_key()))


def load_vapid(private_b64: str, public_b64: str) -> VapidKeys | None:
    private_b64, public_b64 = private_b64.strip(), public_b64.strip()
    if not private_b64 and not public_b64:
        return None
    try:
        raw = b64url_decode(private_b64)
        if len(raw) != 32:
            raise ValueError("length")
        key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
    except ValueError:
        log.warning("VAPID_PRIVATE_KEY is not a P-256 key: browser reminders stay off")
        return None
    public = b64url(_point(key.public_key()))
    if public != public_b64.rstrip("="):
        log.warning("VAPID_PUBLIC_KEY does not belong to VAPID_PRIVATE_KEY: browser reminders stay off")
        return None
    return VapidKeys(key, public)


_ENDPOINT_CHARS = re.compile(r"[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]+")  # RFC 3986 unreserved, sub-delims, ':' '@' '/' '?'
_BAD_PCT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_HOST = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*")


def valid_endpoint(url: str) -> bool:
    """Strict: the whole string is RFC 3986 characters only (no whitespace, control characters or backslash, which
    parsers and httpx read differently), and the parsed host is exactly a known push host or a label before a known
    suffix."""
    if not isinstance(url, str) or len(url) > ENDPOINT_MAX or not _ENDPOINT_CHARS.fullmatch(url) \
            or _BAD_PCT.search(url):
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = parts.hostname or ""
    if parts.scheme != "https" or port not in (None, 443) or parts.username or parts.password or not parts.path \
            or not _HOST.fullmatch(host) or parts.netloc.lower() not in (host, f"{host}:443"):
        return False
    return host in PUSH_HOSTS or any(host.endswith(suffix) and len(host) > len(suffix) for suffix in PUSH_HOST_SUFFIXES)


def endpoint_tag(url) -> str:
    """What the log may say about an endpoint (a personal identifier and the key to its row): a short hash."""
    return hashlib.sha256(str(url).encode("utf-8", "replace")).hexdigest()[:8]


def _browser_key(p256dh: str) -> bytes:
    raw = b64url_decode(p256dh)
    if len(raw) != 65 or raw[0] != 4:
        raise ValueError("p256dh")
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)  # ValueError when not on the curve
    return raw


def valid_keys(p256dh: str, auth: str) -> bool:
    try:
        _browser_key(p256dh)
        return len(b64url_decode(auth)) == 16
    except ValueError:
        return False


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def encrypt(plaintext: bytes, p256dh: str, auth: str, *, sender: ec.EllipticCurvePrivateKey | None = None,
            salt: bytes | None = None) -> bytes:
    """RFC 8291 §3: one aes128gcm record. `sender` and `salt` are fresh for every message; tests pass the RFC's."""
    ua_public = _browser_key(p256dh)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    salt = salt if salt is not None else os.urandom(16)
    as_public = _point(sender.public_key())
    shared = sender.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = _hkdf(b64url_decode(auth), shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    record = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)  # \x02: the last (and only) record
    return salt + struct.pack("!IB", RECORD_SIZE, len(as_public)) + as_public + record


def vapid_authorization(endpoint: str, keys: VapidKeys, subject: str, now: float) -> str:
    parts = urlsplit(endpoint)
    token = jwt.encode({"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(now) + VAPID_TTL_S, "sub": subject},
                       keys.private_key, algorithm="ES256")
    return f"vapid t={token}, k={keys.public_key}"


def push_request(endpoint: str, p256dh: str, auth: str, payload: dict, keys: VapidKeys, subject: str,
                 now: float) -> tuple[dict[str, str], bytes]:
    body = encrypt(json.dumps(payload, separators=(",", ":")).encode(), p256dh, auth)
    headers = {"TTL": str(PUSH_TTL_S), "Urgency": "normal", "Topic": "daily", "Content-Encoding": "aes128gcm",
               "Content-Type": "application/octet-stream",
               "Authorization": vapid_authorization(endpoint, keys, subject, now)}
    return headers, body
