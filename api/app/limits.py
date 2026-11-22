"""Guest cookie, the visitor's local day, the daily limit (readings and paid follow-ups: 2 per guest, 3 per
account, stage 4.3 §5 and 4.4b §2), the IP counters, the follow-up attempts (§4.1, §4.2, §8.2, §8.4, §9.2, §10)."""
import hashlib
import ipaddress
import re
import secrets
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import DAILY_LIMIT, FOLLOWUP_ATTEMPTS, IP_HARD_LIMIT, USER_DAILY_LIMIT

COOKIE_NAME = "ad_guest"
COOKIE_MAX_AGE = 365 * 24 * 3600
IP_DAILY_THRESHOLD = 20
IP_BURST_THRESHOLD = 5
BURST_WINDOW_S = 60.0
DAILY_RATE_LIMIT = 30  # GET /api/daily per address per minute
NO_COUNTRY = {"XX", "T1"}  # Cloudflare: unknown location, and Tor exit nodes
UTC = ZoneInfo("UTC")
_ZONE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*(/[A-Za-z0-9_+-]+)*")  # an IANA name, never a path
# Old names browsers still report (CLDR) whose links Debian's tzdata no longer ships
ZONE_ALIASES = {
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires", "America/Cordoba": "America/Argentina/Cordoba",
    "America/Mendoza": "America/Argentina/Mendoza", "America/Catamarca": "America/Argentina/Catamarca",
    "America/Jujuy": "America/Argentina/Jujuy", "America/Indianapolis": "America/Indiana/Indianapolis",
    "America/Louisville": "America/Kentucky/Louisville", "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Saigon": "Asia/Ho_Chi_Minh", "Asia/Katmandu": "Asia/Kathmandu", "Asia/Rangoon": "Asia/Yangon",
    "Europe/Kiev": "Europe/Kyiv", "Atlantic/Faeroe": "Atlantic/Faroe",
}


class LimitReached(Exception):
    """Raised inside the reading transaction, so the transaction rolls back and nothing is counted."""

    def __init__(self, reason: str):  # "limit" (the day's quota) | "ip_limit" (per address) | "attempts" (per reading)
        super().__init__(reason)
        self.reason = reason


def parse_guest_id(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def guest_from_request(request) -> tuple[uuid.UUID, bool]:
    guest_id = parse_guest_id(request.cookies.get(COOKIE_NAME))
    return (guest_id, False) if guest_id else (uuid.uuid4(), True)


def set_guest_cookie(response, guest_id: uuid.UUID) -> None:
    """A service cookie (random id, no consent banner): HttpOnly, Secure, SameSite=Lax, 1 year."""
    response.set_cookie(COOKIE_NAME, str(guest_id), max_age=COOKIE_MAX_AGE, path="/", secure=True, httponly=True,
                        samesite="lax")


def resolve_tz(name: str | None) -> ZoneInfo:
    """An existing IANA zone, otherwise UTC (§4.1)."""
    name = ZONE_ALIASES.get(name, name) if name else name
    if name and len(name) <= 64 and _ZONE_NAME.fullmatch(name):
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            pass
    return UTC


def local_day(tz: ZoneInfo, now: datetime) -> date:
    return now.astimezone(tz).date()


def utc_day(now: datetime) -> date:
    return now.astimezone(timezone.utc).date()


def guest_subject(guest_id) -> str:
    return f"guest:{guest_id}"


def user_subject(user_id) -> str:
    """Stage 4.3 §5: a signed-in person's readings count per account, on every device."""
    return f"user:{user_id}"


@dataclass(frozen=True)
class Quota:
    """Whose "N per day" a reading or a paid follow-up uses: the usage subject and its daily limit."""
    subject: str
    limit: int


def guest_quota(guest_id) -> Quota:
    return Quota(guest_subject(guest_id), DAILY_LIMIT)


def user_quota(user_id) -> Quota:
    return Quota(user_subject(user_id), USER_DAILY_LIMIT)


def owner_quota(reading) -> Quota:
    """§5: a paid follow-up uses a slot of the reading's owner — its account if it has one, else the guest — and a
    refund goes back to the same place. `reading`: any mapping with guest_id and user_id."""
    return user_quota(reading["user_id"]) if reading.get("user_id") else guest_quota(reading["guest_id"])


def ip_subject(ip_hash: str) -> str:
    return f"ip:{ip_hash}"


def followup_ip_subject(ip_hash: str) -> str:
    return f"ipf:{ip_hash}"


def waitlist_ip_subject(ip_hash: str) -> str:
    """Plus waitlist requests per address per UTC day (stage 4.3 §8)."""
    return f"ipw:{ip_hash}"


def guard_ip_subject(ip_hash: str) -> str:
    """Question checks by the model on POST /api/readings, crisis answers included (§10.5, В18)."""
    return f"ipg:{ip_hash}"


def used(conn, subject: str, day: date) -> int:
    row = conn.execute("SELECT count FROM usage WHERE subject = %s AND day = %s", (subject, day)).fetchone()
    return row["count"] if row else 0


def take_slot(conn, subject: str, day: date, limit: int) -> int | None:
    """Atomic +1 while the counter is below the limit: the new count, or None when the limit is reached.

    Two requests at once wait on the same row, so at most `limit` of them get a count (§8.11).
    """
    row = conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 1)"
                       " ON CONFLICT (subject, day) DO UPDATE SET count = usage.count + 1 WHERE usage.count < %s"
                       " RETURNING count", (subject, day, limit)).fetchone()
    return row["count"] if row else None


def give_back_slot(conn, subject: str, day: date) -> None:
    """-1, never below zero: a paid follow-up that failed returns its reading (§10.1)."""
    conn.execute("UPDATE usage SET count = count - 1 WHERE subject = %s AND day = %s AND count > 0", (subject, day))


def take_reading_slots(conn, quota: Quota, day: date, ip_hash: str, ip_day: date) -> int:
    """One reading for the guest or the account (local day, quota.limit) and the address (UTC day, hard cap 60) in
    the caller's transaction.

    Returns the quota's new count; raises LimitReached, so the caller's transaction (and the reading) rolls back.
    """
    count = take_slot(conn, quota.subject, day, quota.limit)
    if count is None:
        raise LimitReached("limit")
    if take_slot(conn, ip_subject(ip_hash), ip_day, IP_HARD_LIMIT) is None:
        raise LimitReached("ip_limit")
    return count


def take_followup_attempt(conn, reading_id) -> int:
    """One attempt of the reading (§10.2, FOLLOWUP_ATTEMPTS), taken in the transaction that inserts the follow-up:
    after the question check, so a crisis answer of the check takes none (stage 4.5 §3); a reader [[crisis]],
    a refusal and a failure keep it. The UPDATE locks the reading's row until that transaction ends, so the
    follow-ups of one reading are created one at a time.

    Returns the new count, which is also the follow-up's number n — never repeated, even when a follow-up was
    deleted (stage 4.5 §5); raises LimitReached("attempts"), so the caller's transaction rolls back.
    """
    row = conn.execute("UPDATE readings SET followup_attempts = followup_attempts + 1"
                       " WHERE id = %s AND followup_attempts < %s RETURNING followup_attempts",
                       (reading_id, FOLLOWUP_ATTEMPTS)).fetchone()
    if row is None:
        raise LimitReached("attempts")
    return row["followup_attempts"]


def remaining(conn, quota: Quota, day: date) -> int:
    return max(quota.limit - used(conn, quota.subject, day), 0)


def needs_turnstile(burst_hits: int, ip_readings_today: int) -> bool:
    return burst_hits > IP_BURST_THRESHOLD or ip_readings_today >= IP_DAILY_THRESHOLD


def ip_blocked(ip_readings_today: int) -> bool:
    """§8.4: the hard cap; Turnstile does not lift it."""
    return ip_readings_today >= IP_HARD_LIMIT


def ip_key(ip: str) -> str:
    """IPv6 counts by its /64 network (one home or phone gets a whole /64); an IPv4-mapped IPv6 address
    counts as its IPv4 address; IPv4 and anything else as is."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if address.version == 6:
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        # Built from the integer value, so a scope id (fe80::1%eth0) is not part of the network
        return str(ipaddress.IPv6Network(((int(address) >> 64) << 64, 64)))
    return str(address)


class DailySalt:
    """sha256(salt + IP); the salt is random, lives only in memory and is replaced when the UTC date changes."""

    def __init__(self):
        self._day: date | None = None
        self._salt = b""
        self._lock = threading.Lock()

    def hash_ip(self, ip: str, now: datetime) -> str:
        day = utc_day(now)
        with self._lock:
            if day != self._day:
                self._day = day
                self._salt = secrets.token_bytes(32)
            salt = self._salt
        return hashlib.sha256(salt + ip_key(ip).encode()).hexdigest()


class BurstCounter:
    """Requests per key within a sliding window (in memory, one API process).

    Keys with no hit left in the window are dropped at most once per window interval, so a hit is O(1)
    amortized: each prune scans only keys that had a hit in the window before it, and prunes are a window apart.
    """

    def __init__(self, window_s: float = BURST_WINDOW_S):
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}
        self._next_prune = float("-inf")
        self._lock = threading.Lock()

    def _prune(self, t: float) -> None:
        cutoff = t - self.window_s
        self._hits = {k: q for k, q in self._hits.items() if q and q[-1] > cutoff}

    def hit(self, key: str, now: datetime) -> int:
        t = now.timestamp()
        with self._lock:
            if t >= self._next_prune:
                self._prune(t)
                self._next_prune = t + self.window_s
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= t - self.window_s:
                q.popleft()
            q.append(t)
            return len(q)


def client_ip(request, trust_cloudflare: bool) -> str:
    """§8.2. With TRUST_CLOUDFLARE: CF-Connecting-IP (the server then accepts only Cloudflare's addresses).
    Otherwise CF-* headers are ignored: X-Real-IP, which Caddy always overwrites with the TCP peer, then the socket.
    """
    if trust_cloudflare:
        cf = (request.headers.get("cf-connecting-ip") or "").strip()
        if cf:
            return cf
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        return real
    return request.client.host if request.client else "unknown"


def client_country(request, trust_cloudflare: bool) -> str | None:
    """CF-IPCountry only behind Cloudflare; XX (unknown) and T1 (Tor) give None. Used for the crisis answer only,
    never stored."""
    if not trust_cloudflare:
        return None
    code = (request.headers.get("cf-ipcountry") or "").strip().upper()
    if len(code) != 2 or not code.isalpha() or code in NO_COUNTRY:
        return None
    return code
