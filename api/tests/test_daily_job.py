import asyncio
from dataclasses import replace
from datetime import date, datetime, timezone

from app import repo
from app.daily import daily_dates, daily_loop, fill_daily_cache
from app.reader.provider import FakeReply

DAY = date(2026, 11, 20)
TWO = ("major-18-moon", "major-19-sun")


def cache_rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT card_id, reversed, lang, day, prompt_version FROM daily_cache"
                            " ORDER BY card_id, reversed, lang").fetchall()


def test_daily_dates_cover_every_local_day_today_first():
    now = datetime(2026, 11, 20, 3, 0, tzinfo=timezone.utc)
    assert daily_dates(now) == [DAY, date(2026, 11, 21), date(2026, 11, 19)]


def test_fill_writes_every_missing_text_once(api):
    assert fill_daily_cache(api.ctx, DAY, TWO) == {"written": 8, "failed": 0, "budget": False, "stopped": False}
    rows = cache_rows(api)
    assert len(rows) == 8 and {r["prompt_version"] for r in rows} == {"daily.en.v2", "daily.es.v2"}
    assert len(api.reader.stream_calls()) == 8
    assert fill_daily_cache(api.ctx, DAY, TWO) == {"written": 0, "failed": 0, "budget": False, "stopped": False}
    assert len(api.reader.stream_calls()) == 8
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM llm_calls WHERE purpose = 'daily'").fetchone()["n"] == 8


def test_failed_or_rejected_texts_are_retried_by_the_next_run(api):
    # the run's order: (False, en), (False, es), (True, en), (True, es)
    api.reader.replies.extend([FakeReply(fail_after=0), FakeReply(chunks=["Te extraña y volverá pronto."]),
                               FakeReply(chunks=["Half a sentence"], stop_reason="max_tokens")])
    assert fill_daily_cache(api.ctx, DAY, TWO[:1]) == {"written": 1, "failed": 3, "budget": False, "stopped": False}
    assert fill_daily_cache(api.ctx, DAY, TWO[:1]) == {"written": 3, "failed": 0, "budget": False, "stopped": False}
    assert len(cache_rows(api)) == 4


def test_failures_in_a_row_stop_the_run(api):
    api.reader.replies.extend([FakeReply(fail_after=0) for _ in range(6)])
    assert fill_daily_cache(api.ctx, DAY, TWO) == {"written": 0, "failed": 5, "budget": False, "stopped": True}
    assert len(api.reader.stream_calls()) == 5


def test_budget_stops_the_run(api):
    api.ctx.settings = replace(api.ctx.settings, daily_budget_usd=0.0)
    assert fill_daily_cache(api.ctx, DAY, TWO) == {"written": 0, "failed": 0, "budget": True, "stopped": False}
    assert api.reader.stream_calls() == []


def test_daily_loop_runs_now_and_repeats(api):
    async def wait_for(rows: int) -> int:
        for _ in range(100):
            if len(cache_rows(api)) == rows:
                break
            await asyncio.sleep(0.05)
        return len(cache_rows(api))

    async def scenario():
        task = asyncio.create_task(daily_loop(api.ctx, 0.05, TWO[:1]))
        first = await wait_for(12)  # 1 card × 2 orientations × 2 languages × 3 days
        with api.db.connect() as conn:
            conn.execute("DELETE FROM daily_cache WHERE lang = 'es'")
        second = await wait_for(12)
        task.cancel()
        return first, second

    assert asyncio.run(scenario()) == (12, 12)


def test_cached_keys_ignore_other_days(api):
    fill_daily_cache(api.ctx, DAY, TWO[:1])
    with api.db.connect() as conn:
        assert repo.cached_daily_keys(conn, date(2026, 11, 21)) == set()
