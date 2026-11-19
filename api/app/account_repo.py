"""SQL for accounts (spec 2026-11-19 stage 4.3): moving guest readings into an account, profiles, the diary, the
export, account deletion and the Plus waitlist. Every function takes a connection from Database.connect(); the
caller owns the transaction. Nothing here hands a note or an outcome to a model.
"""
import hashlib


def token_hash(token: str) -> str:
    """Only the hash is stored: a copy of the table gives no working claim tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def insert_claim_token(conn, hashed: str, reading_id, now, expires_at) -> None:
    conn.execute("INSERT INTO claim_tokens (token_hash, reading_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
                 (hashed, reading_id, now, expires_at))


def live_claim_tokens(conn, reading_id, now) -> int:
    row = conn.execute("SELECT count(*) AS n FROM claim_tokens WHERE reading_id = %s AND used_at IS NULL"
                       " AND expires_at > %s", (reading_id, now)).fetchone()
    return row["n"]


def claim_device(conn, user_id, guest_id, now) -> list:
    """§4.1: every unexpired reading of this device's guest cookie that has no account yet; returns their ids."""
    rows = conn.execute("UPDATE readings SET user_id = %s, expires_at = NULL WHERE guest_id = %s AND user_id IS NULL"
                        " AND (expires_at IS NULL OR expires_at > %s) RETURNING id",
                        (user_id, guest_id, now)).fetchall()
    return [r["id"] for r in rows]


def claim_by_tokens(conn, user_id, hashes: list[str], now) -> list:
    """§4.2: every live token in the list is used up, once, even when its reading does not move; the reading moves
    only while it has no account and has not expired. Unknown, used or expired tokens are skipped."""
    if not hashes:
        return []
    rows = conn.execute(
        "WITH used AS (UPDATE claim_tokens SET used_at = %(now)s WHERE token_hash = ANY(%(hashes)s)"
        " AND used_at IS NULL AND expires_at > %(now)s RETURNING reading_id)"
        " UPDATE readings r SET user_id = %(user)s, expires_at = NULL FROM used WHERE r.id = used.reading_id"
        " AND r.user_id IS NULL AND (r.expires_at IS NULL OR r.expires_at > %(now)s) RETURNING r.id",
        {"now": now, "hashes": hashes, "user": user_id}).fetchall()
    return list(dict.fromkeys(r["id"] for r in rows))


def ensure_profile(conn, user_id, now) -> dict:
    """The profile is made the first time the API sees the account; its created_at is the account's date here."""
    conn.execute("INSERT INTO profiles (user_id, created_at) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
                 (user_id, now))
    return conn.execute("SELECT * FROM profiles WHERE user_id = %s", (user_id,)).fetchone()
