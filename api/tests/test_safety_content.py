import re

import pytest

from app.config import load_settings
from app.limits import ZONE_ALIASES, resolve_tz
from app.safety.content import (TZ_COUNTRIES, crisis_payload, helplines_for, load_all_texts, load_helplines,
                                resolve_country, soft_line)
from app.terms import find_banned, load_terms

HELP = load_helplines()
TEXTS = load_all_texts()
SOURCES = {
    "988": "https://988lifeline.org/",
    "1-800-799-7233": "https://www.thehotline.org",
    "800 911 2000": "https://politica.expansion.mx/mexico/2025/09/10/"
                    "prevencion-del-suicidio-servicios-y-numeros-de-ayuda-mexico",
    "079": "https://www.nmas.com.mx/sociedad/nueva-linea-de-las-mujeres-numero-telefono-atencion-emergencias-violencia",
    "024": "https://www.sanidad.gob.es/linea024/home.htm",
    "112": "https://www.sanidad.gob.es/linea024/home.htm",
    "135": "https://findahelpline.com/organizations/linea-de-prevencion-del-suicidio-buenos-aires",
    "(011) 5275-1135": "https://findahelpline.com/organizations/linea-de-prevencion-del-suicidio-buenos-aires",
    "106": "https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/VS/PP/ET/"
           "directorio-salud-mental-prevencion-suicidio-minsalud.pdf",
}


def all_lines():
    for record in [*HELP["countries"].values(), HELP["default"]]:
        yield from record["lines"]


def strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in ("lang", "status"):
                yield from strings(item)
    elif isinstance(value, str):
        yield value


def shape(value):
    return {k: shape(v) for k, v in value.items()} if isinstance(value, dict) else None


def test_countries_at_launch():
    assert set(HELP["countries"]) == {"US", "MX", "ES", "AR", "CO"}


def test_lines_have_topic_source_and_check_date():
    for line in all_lines():
        assert line["topic"] in ("crisis", "violence", "emergency", "directory"), line["name"]
        assert line["source"].startswith("https://"), line["name"]
        assert line["checked"] == "2026-11-14", line["name"]
    unverified = {line.get("number") for line in all_lines() if line["verify_before_launch"]}
    assert unverified == {"106", "079", "800 911 2000"}


def test_numbers_and_sources_match_spec():
    numbers = {code: [line["number"] for line in rec["lines"]] for code, rec in HELP["countries"].items()}
    assert numbers == {"US": ["988", "1-800-799-7233"], "MX": ["800 911 2000", "079"], "ES": ["024", "112"],
                       "AR": ["135", "(011) 5275-1135"], "CO": ["106"]}
    assert {line["number"]: line["source"] for line in all_lines() if "number" in line} == SOURCES


def test_violence_lines():
    us = HELP["countries"]["US"]["lines"][1]
    assert (us["topic"], us["sms"], us["hours"]) == ("violence", "START to 88788", "24/7")
    mx = HELP["countries"]["MX"]["lines"][1]
    assert (mx["topic"], mx["note"], mx["hours"]) == ("violence", "opción 1", "24/7")


@pytest.mark.parametrize("country, expected", [("mx", "MX"), ("US", "US"), (None, None), ("FR", None),
                                               ("XX", None)])
def test_helplines_for(country, expected):
    assert helplines_for(HELP, country)["country"] == expected


@pytest.mark.parametrize("cf, tz, lang, expected", [
    ("MX", "Europe/Madrid", "en", ("MX", "cloudflare")),
    ("FR", None, "es", ("FR", "cloudflare")),
    (None, "America/Monterrey", "en", ("MX", "timezone")),
    (None, "America/Buenos_Aires", "es", ("AR", "timezone")),
    (None, "Europe/Paris", "es", (None, "timezone")),
    (None, None, "en", ("US", "language")),
    (None, "Mars/Olympus", "es", ("MX", "language")),
    (None, "UTC", "es", ("MX", "language")),
])
def test_resolve_country(cf, tz, lang, expected):
    assert resolve_country(cf, tz, lang) == expected


def test_timezone_map_is_small_and_valid():
    assert set(TZ_COUNTRIES.values()) == set(HELP["countries"])
    assert all(resolve_tz(tz).key == tz for tz in TZ_COUNTRIES)
    assert all(resolve_tz(old).key == new for old, new in ZONE_ALIASES.items())
    # every old name that maps into a country we list lands on a zone of that country
    covered = ("America/Argentina/", "America/Indiana/", "America/Kentucky/")
    assert all(new in TZ_COUNTRIES for new in ZONE_ALIASES.values() if new.startswith(covered))
    assert TZ_COUNTRIES["America/North_Dakota/Center"] == "US" and TZ_COUNTRIES["America/Juneau"] == "US"


def test_texts_same_keys_and_draft():
    assert TEXTS["en"]["status"] == TEXTS["es"]["status"] == "draft"
    assert shape(TEXTS["en"]) == shape(TEXTS["es"])


def test_texts_have_no_banned_terms():
    banned = load_terms(load_settings({}).banned_terms_path)
    for lang in ("en", "es"):
        for text in strings(TEXTS[lang]):
            assert find_banned(text, banned[lang]) == [], (lang, text)


def test_spanish_texts_use_tu_without_gendered_reader_forms():
    joined = " ".join(strings(TEXTS["es"])).lower()
    gendered = r"\b(usted|lista|listo|segura|seguro|preparada|preparado|bienvenida|bienvenido)\b"
    assert re.search(gendered, joined) is None
    assert "tienes" in joined


@pytest.mark.parametrize("lang, group, expected", [
    ("en", "redirect_money", "This isn't financial advice."),
    ("es", "redirect_money", "Esto no es un consejo financiero."),
    ("en", "redirect_person", TEXTS["en"]["soft_lines"]["redirect_person"]),
    ("es", "redirect_topic", TEXTS["es"]["soft_lines"]["redirect_topic"]),
    ("en", "ok", None),
])
def test_soft_lines(lang, group, expected):
    assert soft_line(TEXTS[lang], group) == expected


def test_crisis_payload_lists_both_kinds_and_orders_by_violence():
    calm = crisis_payload(TEXTS["es"], HELP, "MX", "timezone", violence=False)
    assert calm["group"] == "crisis"
    assert set(calm["crisis"]) == {"title", "body", "not_saved", "contacts_intro", "emergency_line",
                                   "fallback_contacts", "closing"}
    assert calm["helplines"]["country"] == "MX" and calm["helplines"]["source"] == "timezone"
    assert [line["topic"] for line in calm["helplines"]["lines"]] == ["crisis", "violence"]
    assert calm["helplines"]["lines"][1]["purpose"] == TEXTS["es"]["crisis"]["line_purpose"]["violence"]
    hurt = crisis_payload(TEXTS["en"], HELP, "US", "cloudflare", violence=True)
    assert [line["number"] for line in hurt["helplines"]["lines"]] == ["1-800-799-7233", "988"]


def test_crisis_payload_unknown_country_gets_the_directory():
    payload = crisis_payload(TEXTS["en"], HELP, None, "timezone", violence=False)
    assert payload["helplines"]["country"] is None
    assert [line["topic"] for line in payload["helplines"]["lines"]] == ["directory"]
