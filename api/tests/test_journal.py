from datetime import date, timedelta

from app.journal import streaks

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
