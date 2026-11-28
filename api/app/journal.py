"""The Card of the Day as a habit (spec 2026-11-27 stage 8.1): streaks, months of the calendar, the month's most
frequent card. Pure functions over dates and rows; no database, no model. A note or a mark never passes here."""
import re
from collections import Counter
from datetime import date, timedelta
from typing import Iterable

MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
TOP_CARD_MIN = 2  # a card that came once is not "the most frequent": below this the line is not shown


def streaks(days: Iterable[date], today: date) -> tuple[int, int]:
    """(current, best). current: the run of days in a row that ends today, or yesterday while today has no card
    yet (the run is not over until the day is); 0 otherwise. A missed day simply starts a new run (spec §2.6)."""
    run_at: dict[date, int] = {}
    best = 0
    previous: date | None = None
    for day in sorted(set(days)):
        run = run_at[previous] + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        run_at[day] = run
        best = max(best, run)
        previous = day
    current = run_at.get(today) or run_at.get(today - timedelta(days=1)) or 0
    return current, best


def parse_month(text: str) -> date | None:
    """"2026-11" → date(2026, 11, 1); anything else → None."""
    match = MONTH.fullmatch(text)
    return date(int(match.group(1)), int(match.group(2)), 1) if match else None


def next_month(first: date) -> date:
    return date(first.year + (first.month == 12), first.month % 12 + 1, 1)


def previous_month(first: date) -> date:
    return date(first.year - (first.month == 1), (first.month - 2) % 12 + 1, 1)


def month_key(first: date) -> str:
    return f"{first.year:04d}-{first.month:02d}"


def free_months(today: date) -> tuple[date, date]:
    """Spec §2: the free calendar shows the current and the previous month (first days); older ones are kept."""
    current = today.replace(day=1)
    return previous_month(current), current


def top_card(rows: list[dict]) -> tuple[str, int] | None:
    """The card (by id, either orientation) that came most often among `rows`, with its count; a tie goes to the card
    that came last. None when no card came at least TOP_CARD_MIN times."""
    counts = Counter(row["card_id"] for row in rows)
    if not counts:
        return None
    last = {row["card_id"]: row["day"] for row in rows}
    card_id = max(counts, key=lambda c: (counts[c], last[c]))
    return (card_id, counts[card_id]) if counts[card_id] >= TOP_CARD_MIN else None
