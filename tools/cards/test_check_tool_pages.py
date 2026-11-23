"""Тесты проверки страниц-инструментов (tools/cards/check_tool_pages.py)."""
import copy

import check_pages as cp
import check_tool_pages as tp

CTX = cp.load_context()
BASE = {"schema": 1, "page_id": "daily", "lang": "en", "url": "/daily", "status": "draft",
        "title": "Daily Tarot Card: Draw Your Card of the Day", "description": "d" * 140,
        "h1": "Daily tarot: your card for today", "lead": "One card each morning.", "capsule": None,
        "blocks": [{"id": "what", "heading": "What is a card of the day?", "paragraphs": ["calm words " * 280]}],
        "faq": [{"q": "Is it free?", "a": "Yes, {guest_limit} a day."}] * 3,
        "intents": [{"q": f"question {i}", "source": "[PAA]", "answered_in": "what"} for i in range(10)]}


def errors(page, path="content/pages/en/daily.json"):
    return tp.check(page, path, CTX, {})[0]


def has(errs, part):
    return any(part in e for e in errs)


def test_good_page_passes():
    assert errors(copy.deepcopy(BASE)) == []


def test_intents_gate():
    p = copy.deepcopy(BASE)
    p["intents"] = p["intents"][:9]
    assert has(errors(p), "intents")
    p = copy.deepcopy(BASE)
    p["intents"][0]["answered_in"] = "faq:9"
    assert has(errors(p), "answered_in")


def test_placeholders_and_banned():
    p = copy.deepcopy(BASE)
    p["faq"][0] = {"q": "Limit?", "a": "{daily_cap} a day."}
    assert has(errors(p), "метка")
    p = copy.deepcopy(BASE)
    p["blocks"][0]["paragraphs"].append("It is 100% accurate and he loves you.")
    assert has(errors(p), "запрещённые слова") and has(errors(p), "точности")


def test_word_limits_and_capsule():
    p = copy.deepcopy(BASE)
    p["blocks"][0]["paragraphs"] = ["short"]
    assert has(errors(p), "объём")
    p = copy.deepcopy(BASE)
    p["capsule"] = "Not allowed here."
    assert has(errors(p), "capsule")


def test_spanish_headings_are_questions():
    p = copy.deepcopy(BASE)
    p.update(lang="es", page_id="carta-del-dia", url="/es/carta-del-dia")
    p["blocks"][0]["heading"] = "Qué es la carta del día"
    assert has(errors(p, "content/pages/es/carta-del-dia.json"), "¿…?")
