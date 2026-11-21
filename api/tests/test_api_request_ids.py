"""Stage 4.5 §5 (review gaps): the request_id twins at the last slot, and a repeated crisis question."""
import threading
import uuid

from helpers import guest_headers, post_reading

MX = "America/Mexico_City"


def guest_usage(api) -> int:
    with api.db.connect() as conn:
        return conn.execute("SELECT coalesce(sum(count), 0) AS n FROM usage WHERE subject LIKE 'guest:%'").fetchone()["n"]


def reading_count(api) -> int:
    with api.db.connect() as conn:
        return conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"]


def guard_rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT lang, guard_group, source, count FROM guard_events ORDER BY guard_group").fetchall()


def test_twins_at_the_last_slot_both_get_the_reading(api):
    """Pins "insert before slots": the winner takes the guest's last slot; the loser waits on the insert, then
    finds the winner's reading. With the slots taken first the loser would be refused with 429 limit."""
    guest, number = uuid.uuid4(), str(uuid.uuid4())
    for _ in range(2):  # two of the three daily slots are used
        assert post_reading(api.new_client(), kind="one", tz=MX, headers=guest_headers(guest)).status_code == 201
    api.guard.json_delay = 0.3  # both wait in the question check, then race to insert
    start = threading.Barrier(2)
    answers = []

    def worker():
        client = api.new_client()
        start.wait()
        answers.append(post_reading(client, kind="one", tz=MX, question="What helps me focus?", request_id=number,
                                    headers=guest_headers(guest)))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [a.status_code for a in answers] == [201, 201]
    assert answers[0].json()["id"] == answers[1].json()["id"]
    assert [a.json()["remaining"] for a in answers] == [0, 0]
    assert (guest_usage(api), reading_count(api)) == (3, 3)


def test_a_crisis_question_repeated_with_one_number_is_checked_again(api):
    """A crisis answer makes no reading, so its number finds nothing: the question check runs every time."""
    number = str(uuid.uuid4())
    ask = dict(kind="one", tz=MX, question="I want to die", request_id=number)
    first = post_reading(api.client, **ask)
    again = post_reading(api.client, **ask)
    assert (first.status_code, again.status_code) == (200, 200)
    assert first.json()["group"] == "crisis" and again.json()["group"] == "crisis"
    assert (reading_count(api), guest_usage(api)) == (0, 0)
    assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "terms", "count": 2}]  # checked twice
