"""SQL for accounts (spec 2026-11-19 stage 4.3): moving guest readings into an account, profiles, the diary, the
export, account deletion and the Plus waitlist. Every function takes a connection from Database.connect(); the
caller owns the transaction. Nothing here hands a note or an outcome to a model.
"""
import hashlib

from app.auth import AuthError


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
    """§4.1: every unexpired reading of this device's guest cookie that has no account yet; returns their ids.
    The request number goes (stage 4.5 §5): it is unique per owner, and the account may hold the same one."""
    rows = conn.execute("UPDATE readings SET user_id = %s, expires_at = NULL, request_id = NULL"
                        " WHERE guest_id = %s AND user_id IS NULL"
                        " AND (expires_at IS NULL OR expires_at > %s) RETURNING id",
                        (user_id, guest_id, now)).fetchall()
    return [r["id"] for r in rows]


def claim_by_tokens(conn, user_id, hashes: list[str], now) -> list:
    """§4.2: every live token in the list is used up, once, even when its reading does not move; the reading moves
    only while it has no account and has not expired. Unknown, used or expired tokens are skipped. A moved reading
    drops its request number, as in claim_device."""
    if not hashes:
        return []
    rows = conn.execute(
        "WITH used AS (UPDATE claim_tokens SET used_at = %(now)s WHERE token_hash = ANY(%(hashes)s)"
        " AND used_at IS NULL AND expires_at > %(now)s RETURNING reading_id)"
        " UPDATE readings r SET user_id = %(user)s, expires_at = NULL, request_id = NULL FROM used"
        " WHERE r.id = used.reading_id"
        " AND r.user_id IS NULL AND (r.expires_at IS NULL OR r.expires_at > %(now)s) RETURNING r.id",
        {"now": now, "hashes": hashes, "user": user_id}).fetchall()
    return list(dict.fromkeys(r["id"] for r in rows))


def claim_daily(conn, user_id, guest_id) -> int:
    """Stage 8.1 §3: signing in moves this cookie's cards of the day into the account; on a day the account already
    has a card, the account's card stays and the device's card of that day goes. Returns the number moved."""
    conn.execute("DELETE FROM daily_draws g WHERE g.guest_id = %s"
                 " AND EXISTS (SELECT 1 FROM daily_draws a WHERE a.user_id = %s AND a.day = g.day)", (guest_id, user_id))
    return conn.execute("UPDATE daily_draws SET user_id = %s, guest_id = NULL WHERE guest_id = %s",
                        (user_id, guest_id)).rowcount


def claim_push(conn, user_id, guest_id) -> int:
    """This cookie's browser reminders follow the cards into the account (the "card already open" check then looks
    at the account's card)."""
    return conn.execute("UPDATE push_subscriptions SET user_id = %s, guest_id = NULL WHERE guest_id = %s",
                        (user_id, guest_id)).rowcount


def ensure_profile(conn, user_id, now) -> dict:
    """The profile is made the first time the API sees the account; its created_at is the account's date here.
    A deleted account is refused first, so its still-valid token cannot bring the profile back."""
    lock_account(conn, user_id)  # takes turns with delete_account
    refuse_deleted(conn, user_id)
    conn.execute("INSERT INTO profiles (user_id, created_at) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
                 (user_id, now))
    return conn.execute("SELECT * FROM profiles WHERE user_id = %s", (user_id,)).fetchone()


def diary_page(conn, user_id, before, limit: int) -> list[dict]:
    """§6: the account's readings, newest first, older than `before` (None: from the newest), with the number of
    answered follow-ups."""
    return conn.execute(
        "SELECT r.*, (SELECT count(*) FROM followups f WHERE f.reading_id = r.id AND f.answer IS NOT NULL AND f.answer ->> 'crisis' IS NULL)"
        " AS followup_count FROM readings r WHERE r.user_id = %s"
        " AND (%s::timestamptz IS NULL OR r.created_at < %s) ORDER BY r.created_at DESC, r.id DESC LIMIT %s",
        (user_id, before, before, limit)).fetchall()


def diary_count(conn, user_id) -> int:
    """Stage 4.4b §5: every reading of the account, the ones hidden beyond the free diary's list included."""
    return conn.execute("SELECT count(*) AS n FROM readings WHERE user_id = %s", (user_id,)).fetchone()["n"]


DIARY_FIELDS = "outcome, outcome_at, note, note_updated_at"


def update_diary_entry(conn, reading_id, user_id, fields: dict, now) -> dict | None:
    """§6: only the fields present in `fields` ("outcome", "note") change; their time is `now`, or NULL when the
    field is cleared. None when the reading is not this account's."""
    sets = []
    if "outcome" in fields:
        sets.append("outcome = %(outcome)s,"
                    " outcome_at = CASE WHEN %(outcome)s::text IS NULL THEN NULL ELSE %(now)s END")
    if "note" in fields:
        sets.append("note = %(note)s, note_updated_at = CASE WHEN %(note)s::text IS NULL THEN NULL ELSE %(now)s END")
    params = {"id": reading_id, "user": user_id, "now": now, "outcome": fields.get("outcome"),
              "note": fields.get("note")}
    where = " WHERE id = %(id)s AND user_id = %(user)s"
    if not sets:
        return conn.execute(f"SELECT {DIARY_FIELDS} FROM readings{where}", params).fetchone()
    return conn.execute(f"UPDATE readings SET {', '.join(sets)}{where} RETURNING {DIARY_FIELDS}", params).fetchone()


def delete_diary_entry(conn, reading_id, user_id) -> bool:
    """§6: the reading goes with its follow-ups and claim tokens (ON DELETE CASCADE); llm_calls keep no text."""
    row = conn.execute("DELETE FROM readings WHERE id = %s AND user_id = %s RETURNING id",
                       (reading_id, user_id)).fetchone()
    return row is not None


def set_consent(conn, user_id, consent: bool, now) -> dict:
    """§8: reminder e-mails, off by default. consent_at is when the consent was given (kept while it stays on),
    NULL when it is off."""
    ensure_profile(conn, user_id, now)
    return conn.execute("UPDATE profiles SET reminders_consent = %(on)s,"
                        " consent_at = CASE WHEN %(on)s THEN coalesce(consent_at, %(now)s) ELSE NULL END"
                        " WHERE user_id = %(user)s RETURNING *", {"on": consent, "now": now, "user": user_id}).fetchone()


def export_readings(conn, user_id) -> list[tuple[dict, list[dict]]]:
    """§8: every reading of the account, oldest first, each with its follow-ups."""
    readings = conn.execute("SELECT * FROM readings WHERE user_id = %s ORDER BY created_at, id",
                            (user_id,)).fetchall()
    followups: dict = {}
    for row in conn.execute("SELECT f.* FROM followups f JOIN readings r ON r.id = f.reading_id"
                            " WHERE r.user_id = %s ORDER BY f.n", (user_id,)).fetchall():
        followups.setdefault(row["reading_id"], []).append(row)
    return [(reading, followups.get(reading["id"], [])) for reading in readings]


def export_daily(conn, user_id) -> list[dict]:
    """Stage 8.1 §3: every card of the day of the account, oldest first, with its mark and note."""
    return conn.execute("SELECT day, card_id, reversed, felt, note, noted_at FROM daily_draws WHERE user_id = %s"
                        " ORDER BY day", (user_id,)).fetchall()


def export_push(conn, user_id) -> list[dict]:
    """The account's browser reminders; the export names the push service, not the endpoint or its keys."""
    return conn.execute("SELECT endpoint, hour, tz, lang, created_at, last_sent_day FROM push_subscriptions"
                        " WHERE user_id = %s ORDER BY created_at", (user_id,)).fetchall()


def waitlist_entry(conn, user_id, email: str | None) -> dict | None:
    return conn.execute("SELECT email, lang, created_at FROM plus_waitlist WHERE user_id = %s OR email = %s"
                        " ORDER BY created_at LIMIT 1", (user_id, email)).fetchone()


def join_waitlist(conn, email: str, lang: str, user_id, now) -> None:
    """§8: one row per e-mail; a repeat is no error and keeps the first language; a signed-in repeat links the
    account to an entry made as a guest."""
    conn.execute("INSERT INTO plus_waitlist (email, lang, user_id, created_at) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (email) DO UPDATE SET user_id = coalesce(plus_waitlist.user_id, EXCLUDED.user_id)",
                 (email, lang, user_id, now))


def refuse_deleted(conn, user_id) -> None:
    """§8: an access token outlives the account it was issued for (until its exp). Such a token writes nothing:
    401 "auth", and the browser's refresh fails, which signs it out."""
    if conn.execute("SELECT 1 FROM deleted_accounts WHERE user_id = %s", (user_id,)).fetchone():
        raise AuthError("deleted account")


def lock_account(conn, user_id) -> None:
    """Held until the transaction ends: deleting an account and creating a reading for it take turns, so a reading
    cannot be written after the delete has looked and before it has committed."""
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (str(user_id),))


def delete_account(conn, user_id, email: str | None, now) -> dict[str, int]:
    """§8: everything of the account at once — its readings (their follow-ups and claim tokens go with them), the
    profile, its cards of the day with their marks and notes and its browser reminders (stage 8.1), the Plus
    waitlist entry and, where the database has Supabase's auth schema, the Supabase user itself;
    the id goes into deleted_accounts so a still-valid token cannot write again. llm_calls stay (no text); the
    account's day counter in usage (a number) expires with the other counters."""
    lock_account(conn, user_id)
    refuse_deleted(conn, user_id)  # a repeat DELETE with a still-valid token: 401, not a second deletion
    conn.execute("INSERT INTO deleted_accounts (user_id, deleted_at) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
                 (user_id, now))
    counts = {
        "readings": conn.execute("DELETE FROM readings WHERE user_id = %s", (user_id,)).rowcount,
        "profiles": conn.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,)).rowcount,
        "daily_draws": conn.execute("DELETE FROM daily_draws WHERE user_id = %s", (user_id,)).rowcount,
        "push_subscriptions": conn.execute("DELETE FROM push_subscriptions WHERE user_id = %s", (user_id,)).rowcount,
        "plus_waitlist": conn.execute("DELETE FROM plus_waitlist WHERE user_id = %s OR email = %s",
                                      (user_id, email)).rowcount,
    }
    if conn.execute("SELECT to_regclass('auth.users') IS NOT NULL AS present").fetchone()["present"]:
        counts["auth_users"] = conn.execute("DELETE FROM auth.users WHERE id = %s", (user_id,)).rowcount
    return counts
