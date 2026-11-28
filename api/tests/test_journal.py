from datetime import date, timedelta

from app.journal import free_months, month_key, next_month, parse_month, previous_month, streaks, top_card

D = date(2026, 11, 27)


def days(*offsets: int) -> list[date]:
    return [D - timedelta(days=n) for n in offsets]


def test_a_streak_counts_the_days_in_a_row_up_to_today():
    assert streaks(days(0, 1, 2, 3), D) == (4, 4)


def test_today_without_a_card_keeps_yesterdays_run_alive():
    assert streaks(days(1, 2, 3), D) == (3, 3)


def test_a_missed_day_starts_again_and_the_best_run_stays():
    assert streaks(days(0, 2, 3, 4, 5, 6), D) == (1, 5)
    assert streaks(days(2, 3), D) == (0, 2)


def test_no_cards_no_streak():
    assert streaks([], D) == (0, 0)


def test_repeated_days_count_once():
    assert streaks(days(0, 0, 1), D) == (2, 2)


def test_months():
    assert parse_month("2026-11") == date(2026, 11, 1)
    for bad in ("2026-13", "2026-1", "26-11", "2026-11-01", "", "2026-00", "0000-01", "9999-12", "2101-01", "２０２６-11"):
        assert parse_month(bad) is None
    assert next_month(date(2026, 12, 1)) == date(2027, 1, 1)
    assert previous_month(date(2026, 1, 1)) == date(2025, 12, 1)
    assert month_key(date(2026, 3, 1)) == "2026-03"
    assert free_months(date(2026, 1, 15)) == (date(2025, 12, 1), date(2026, 1, 1))


def test_top_card_needs_two_and_a_tie_goes_to_the_latest():
    rows = [{"card_id": "a", "day": D - timedelta(days=5)}, {"card_id": "b", "day": D - timedelta(days=4)},
            {"card_id": "a", "day": D - timedelta(days=3)}, {"card_id": "b", "day": D - timedelta(days=1)}]
    assert top_card(rows) == ("b", 2)
    assert top_card(rows[:2]) is None
    assert top_card([]) is None
