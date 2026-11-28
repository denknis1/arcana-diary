"""The Card of the Day as a habit (spec 2026-11-27 stage 8.1): streaks, months of the calendar, the month's most
frequent card. Pure functions over dates and rows; no database, no model. A note or a mark never passes here."""
from datetime import date, timedelta
from typing import Iterable


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
