import io
import urllib.error

import pytest

import fetch_sources
from fetch_sources import card_id_for, match_cards
from validate_cards import load_cards_csv

ROWS = load_cards_csv()


def test_major_titles():
    assert card_id_for("File:RWS1909 - 00 Fool.jpeg", ROWS) == "major-00-fool"
    assert card_id_for("File:RWS1909 - 02 High Priestess.jpeg", ROWS) == "major-02-high-priestess"
    assert card_id_for("File:RWS1909 - 10 Wheel of Fortune.jpeg", ROWS) == "major-10-wheel-of-fortune"


def test_minor_titles():
    assert card_id_for("File:RWS1909 - Cups 14.jpeg", ROWS) == "cups-14-king"
    assert card_id_for("File:RWS1909 - Wands 01.jpeg", ROWS) == "wands-01-ace"


def test_other_files_skipped():
    assert card_id_for("File:Waite–Smith Tarot Roses and Lilies.jpg", ROWS) is None
    assert card_id_for("File:RWS Tarot 18 Moon.jpg", ROWS) is None


def entry(title):
    return {"commons_title": title, "url": "u", "width": 1, "height": 1, "bytes": 1, "sha1": "s"}


def test_match_reports_missing_and_duplicate():
    files = [entry("File:RWS1909 - 00 Fool.jpeg"), entry("File:RWS1909 - 00 Fool.jpg")]
    entries, errors = match_cards(files, ROWS)
    assert len(entries) == 1
    assert any("две картинки для major-00-fool" in e for e in errors)
    assert any("нет файлов для" in e and "cups-14-king" in e for e in errors)


def fake_urlopen(responses, calls):
    def urlopen(req, timeout):
        calls.append(req.full_url)
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return io.BytesIO(r)
    return urlopen


def http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("https://upload.wikimedia.org/x", code, "err", headers, None)


def test_fetch_waits_retry_after_on_429(monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(fetch_sources.urllib.request, "urlopen", fake_urlopen([http_error(429, "7"), b"scan"], calls))
    monkeypatch.setattr(fetch_sources.time, "sleep", sleeps.append)
    assert fetch_sources._fetch("https://upload.wikimedia.org/x") == b"scan"
    assert len(calls) == 2 and sleeps == [7]


def test_fetch_does_not_retry_404(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch_sources.urllib.request, "urlopen", fake_urlopen([http_error(404)], calls))
    monkeypatch.setattr(fetch_sources.time, "sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        fetch_sources._fetch("https://upload.wikimedia.org/x")
    assert len(calls) == 1
