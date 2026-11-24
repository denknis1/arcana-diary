"""Crisis answer, helplines, soft lines and UI texts (§3.2, §3.3, §8.1, §8.2, §8.7).

The country for the helplines is used for this one answer only and never stored:
CF-IPCountry when TRUST_CLOUDFLARE is on; otherwise the browser's time zone (TZ_COUNTRIES); otherwise the language.
Both kinds of lines are always listed (crisis and violence); when the guard saw violence, violence lines come first.
"""
import json
from pathlib import Path

from app.limits import resolve_tz

SAFETY_DIR = Path(__file__).resolve().parent
LANGS = ("en", "es")
CRISIS_KEYS = ("title", "body", "not_saved", "contacts_intro", "emergency_line", "fallback_contacts", "closing")
# Small and explicit (§8.2): only the countries in helplines.json, by canonical IANA zones
# (old names such as America/Buenos_Aires are mapped by limits.ZONE_ALIASES first).
TZ_COUNTRIES = {
    **{tz: "US" for tz in ("America/New_York", "America/Detroit", "America/Chicago", "America/Denver",
                           "America/Phoenix", "America/Los_Angeles", "America/Anchorage", "America/Boise",
                           "America/Indiana/Indianapolis", "America/Indiana/Knox", "America/Indiana/Marengo",
                           "America/Indiana/Petersburg", "America/Indiana/Tell_City", "America/Indiana/Vevay",
                           "America/Indiana/Vincennes", "America/Indiana/Winamac", "America/Kentucky/Louisville",
                           "America/Kentucky/Monticello", "America/North_Dakota/Beulah",
                           "America/North_Dakota/Center", "America/North_Dakota/New_Salem", "America/Menominee",
                           "America/Juneau", "America/Sitka", "America/Nome", "America/Yakutat",
                           "America/Metlakatla", "America/Adak", "Pacific/Honolulu", "America/Puerto_Rico")},
    **{tz: "MX" for tz in ("America/Mexico_City", "America/Monterrey", "America/Merida", "America/Cancun",
                           "America/Chihuahua", "America/Ciudad_Juarez", "America/Hermosillo", "America/Mazatlan",
                           "America/Tijuana", "America/Bahia_Banderas", "America/Matamoros", "America/Ojinaga")},
    **{tz: "ES" for tz in ("Europe/Madrid", "Atlantic/Canary", "Africa/Ceuta")},
    **{tz: "AR" for tz in ("America/Argentina/Buenos_Aires", "America/Argentina/Cordoba",
                           "America/Argentina/Mendoza", "America/Argentina/Salta", "America/Argentina/Tucuman",
                           "America/Argentina/Ushuaia", "America/Argentina/Jujuy", "America/Argentina/Catamarca",
                           "America/Argentina/La_Rioja", "America/Argentina/San_Juan", "America/Argentina/San_Luis",
                           "America/Argentina/Rio_Gallegos")},
    "America/Bogota": "CO",
}
LANG_COUNTRIES = {"en": "US", "es": "MX"}
GROUP_SOFT_LINES = ("redirect_topic", "redirect_person", "redirect_money")


def _load(name: str) -> dict:
    return json.loads((SAFETY_DIR / name).read_text(encoding="utf-8"))


def load_texts(lang: str) -> dict:
    return _load(f"texts.{lang}.json")


def load_all_texts() -> dict[str, dict]:
    return {lang: load_texts(lang) for lang in LANGS}


def load_helplines() -> dict:
    return _load("helplines.json")


def soft_line(texts: dict, group: str) -> str | None:
    """The line above the answer (stage 4.8, decisions 48–49): the themes of the cards, no prediction or advice
    (topic); what the cards mean, not another person's mind (person); not financial advice (money)."""
    return texts["soft_lines"].get(group) if group in GROUP_SOFT_LINES else None


def resolve_country(cf_country: str | None, tz_name: str | None, lang: str) -> tuple[str | None, str]:
    """(country or None, how it was found). A known zone outside our list gives None: the directory only."""
    if cf_country:
        return cf_country.upper(), "cloudflare"
    zone = resolve_tz(tz_name).key
    if zone in TZ_COUNTRIES:
        return TZ_COUNTRIES[zone], "timezone"
    if zone != "UTC" and not zone.startswith("Etc/"):
        return None, "timezone"
    return LANG_COUNTRIES[lang], "language"


def helplines_for(helplines: dict, country: str | None) -> dict:
    code = (country or "").strip().upper()
    return helplines["countries"].get(code, helplines["default"])


def crisis_payload(texts: dict, helplines: dict, country: str | None, source: str, violence: bool) -> dict:
    crisis = texts["crisis"]
    record = helplines_for(helplines, country)
    first = "violence" if violence else "crisis"
    ordered = sorted(record["lines"], key=lambda line: 0 if line["topic"] == first else 1)
    lines = [{**line, "purpose": crisis["line_purpose"][line["topic"]]} for line in ordered]
    return {
        "group": "crisis",
        "crisis": {key: crisis[key] for key in CRISIS_KEYS},
        "helplines": {"country": record["country"], "source": source, "lines": lines},
    }
