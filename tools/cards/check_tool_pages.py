"""Проверка текстов страниц-инструментов и хабов content/pages/{en,es}/*.json по плану
docs/research/stage5/50-tools-page-plan.md (только стандартная библиотека и словари проекта).

Запуск из корня репозитория:
  python3 -I tools/cards/check_tool_pages.py                 — все страницы
  python3 -I tools/cards/check_tool_pages.py FILE [FILE ...] — выбранные (совпадения — со всеми страницами языка)
Код выхода 0 — ошибок нет, 1 — есть ошибки.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_pages as cp  # noqa: E402

ROOT = cp.ROOT
PAGES = ROOT / "content/pages"
CARD_PAGES = cp.PAGES

# page_id → (url, слов min, max, нужна ли капсула; None — служебная страница: капсула, FAQ и интенты не обязательны,
# заголовки ES — не обязательно вопросы)
PLAN = {
    "en": {
        "home": ("/", 800, 1000, False), "one-card": ("/one-card", 600, 800, False),
        "daily": ("/daily", 500, 700, False), "yes-no": ("/yes-no", 600, 800, False),
        "yes-no-cards": ("/yes-no/cards", 900, 1200, True), "love": ("/love", 1000, 1300, False),
        "cards": ("/cards", 1000, 1300, True), "major-arcana": ("/cards/major-arcana", 1200, 1500, True),
        "about": ("/about", 400, 900, None), "how-readings-work": ("/how-readings-work", 800, 1500, None),
        "contact": ("/contact", 80, 400, None), "privacy": ("/privacy", 1200, 3000, None),
        "terms": ("/terms", 1000, 2500, None),
    },
    "es": {
        "home": ("/es", 1200, 1400, False), "carta-del-dia": ("/es/carta-del-dia", 800, 1000, False),
        "si-o-no": ("/es/si-o-no", 1000, 1300, False), "amor": ("/es/amor", 1200, 1500, False),
        "tres-cartas": ("/es/tiradas/3-cartas", 1000, 1300, False), "cartas": ("/es/cartas", 1300, 1600, True),
        "arcanos-mayores": ("/es/cartas/arcanos-mayores", 1800, 2200, True),
        "sobre-nosotros": ("/es/sobre-nosotros", 400, 900, None),
        "como-funcionan-las-lecturas": ("/es/como-funcionan-las-lecturas", 800, 1500, None),
        "contacto": ("/es/contacto", 80, 400, None), "privacidad": ("/es/privacidad", 1200, 3000, None),
        "terminos": ("/es/terminos", 1000, 2500, None),
    },
}
FIELDS = {"schema", "page_id", "lang", "url", "status", "title", "description", "h1", "lead", "capsule", "blocks",
          "faq", "intents"}
PLACEHOLDERS = {"guest_limit", "user_limit", "followups", "diary_free", "yes_count", "no_count", "unclear_count",
                # служебные страницы: пока оператор не выбран (решение 3), публиковать нельзя
                "operator_name", "operator_address", "contact_email", "jurisdiction", "effective_date",
                "hosting_provider", "email_provider", "editor_name"}
INTENTS_MIN = 10
# Правовые страницы: оговорки о гарантиях и суде нужны по сути («no guarantee», «courts of …»).
LEGAL = {"privacy", "terms", "privacidad", "terminos"}
LEGAL_OK = {"guarantee*", "court", "lawsuit", "garantiz*", "tribunal*", "demanda judicial"}
LEGAL_HARSH_OK = {r"lawsuits?", r"pleitos?", r"demanda judicial"}
FAQ_COUNT = (3, 8)
SLACK = 0.10  # допуск по объёму сверх плана (±10 %)


def texts(page: dict) -> list[str]:
    out = [page.get("lead") or "", page.get("capsule") or ""]
    for b in page.get("blocks", []):
        out += b.get("paragraphs", [])
    out += [f.get("a", "") for f in page.get("faq", [])]
    return [t for t in out if t]


def units(page: dict) -> list[str]:
    return [page.get(k) or "" for k in ("title", "description", "h1")] + texts(page) + \
        [b.get("heading", "") for b in page.get("blocks", [])] + [f.get("q", "") for f in page.get("faq", [])]


def check(page: dict, path: str, ctx, others: dict) -> tuple[list[str], list[str], str]:
    errs, warns = [], []
    err, warn = errs.append, warns.append
    lang, pid = page.get("lang"), page.get("page_id")
    if set(page) != FIELDS:
        err(f"поля: лишние {sorted(set(page) - FIELDS)}, нет {sorted(FIELDS - set(page))}")
    if lang not in PLAN or pid not in PLAN[lang]:
        return [f"page_id {pid!r} / lang {lang!r} нет в плане"], [], ""
    url, lo, hi, need_capsule = PLAN[lang][pid]
    service = need_capsule is None
    if Path(path).stem != pid or Path(path).parent.name != lang:
        err("имя файла = page_id, папка = lang")
    if page.get("url") != url:
        err(f"url {page.get('url')!r} ≠ {url!r}")
    if page.get("schema") != 1 or page.get("status") not in cp.STATUSES:
        err("schema 1, status draft/reviewed/published")
    title, desc, h1 = page.get("title", ""), page.get("description", ""), page.get("h1", "")
    if not 0 < len(title) <= cp.TITLE_MAX:
        err(f"title {len(title)} знаков (≤ {cp.TITLE_MAX})")
    if not cp.DESCRIPTION[0] <= len(desc) <= cp.DESCRIPTION[1]:
        err(f"description {len(desc)} знаков ({cp.DESCRIPTION[0]}–{cp.DESCRIPTION[1]})")
    if not h1 or not page.get("lead"):
        err("нужны h1 и lead")
    cap = page.get("capsule")
    if need_capsule:
        if not cap or not cp.CAPSULE_WORDS[0] <= cp.word_count(cap) <= cp.CAPSULE_WORDS[1]:
            err(f"capsule: {cp.word_count(cap or '')} слов ({cp.CAPSULE_WORDS[0]}–{cp.CAPSULE_WORDS[1]})")
    elif cap is not None and not service:
        err("capsule: на этой странице — null (инструмент сверху)")
    blocks = page.get("blocks", [])
    ids = [b.get("id") for b in blocks]
    if len(ids) != len(set(ids)) or not all(ids):
        err("blocks: id пустые или повторяются")
    for b in blocks:
        if not b.get("heading") or not b.get("paragraphs"):
            err(f"blocks[{b.get('id')}]: нужны heading и paragraphs")
        if lang == "es" and not service and not re.match(r"^¿.+\?$", b.get("heading", "").strip()):
            err(f"ES-заголовок — вопрос «¿…?»: {b.get('heading')!r}")
    faq = page.get("faq", [])
    if not (0 if service else FAQ_COUNT[0]) <= len(faq) <= FAQ_COUNT[1]:
        err(f"faq: {len(faq)} вопросов ({FAQ_COUNT[0]}–{FAQ_COUNT[1]})")
    # --- интенты (ворота «≥ 10 интентов», решение 25) ---
    intents = page.get("intents", [])
    if not service and len(intents) < INTENTS_MIN:
        err(f"intents: {len(intents)} < {INTENTS_MIN}")
    targets = set(ids) | {f"faq:{i}" for i in range(len(faq))} | ({"capsule"} if cap else set())
    for it in intents:
        if not it.get("q") or not it.get("source"):
            err(f"intents: нужны q и source: {it}")
        if it.get("answered_in") not in targets:
            err(f"intents: answered_in {it.get('answered_in')!r} нет на странице («{it.get('q', '')[:50]}»)")
    # --- объём ---
    n = sum(cp.word_count(t) for t in texts(page))
    if not lo * (1 - SLACK) <= n <= hi * (1 + SLACK):
        err(f"объём {n} слов, план {lo}–{hi} (±10 %)")
    elif not lo <= n <= hi:
        warn(f"объём {n} слов — вне плана {lo}–{hi}, но в допуске")
    # --- метки фактов, запреты, испанский ---
    for t in units(page):
        for ph in re.findall(r"\{(\w+)\}", t):
            if ph not in PLACEHOLDERS:
                err(f"метка {{{ph}}} не из списка {sorted(PLACEHOLDERS)}")
    terms = cp.live_terms(ctx.reader_terms, lang)
    harsh_rx = [re.compile(r"(?<!\w)" + h + r"(?!\w)", re.I) for h in cp.HARSH[lang]]
    names = list(ctx.names[lang].values())
    for t in units(page):
        hits, _ = cp.find_claims(t, terms, lang)
        clean = re.sub(r"\bcourt cards?\b", " ", t, flags=re.I)
        hits += [w for w, rx in ctx.base_terms[lang] if rx.search(clean)]
        if pid in LEGAL:
            hits = [h for h in hits if h not in LEGAL_OK]
        if hits:
            err(f"запрещённые слова {sorted(set(hits))}: «{t[:70]}»")
        if re.search(cp.NO_CORRESPONDENCE[lang], t, re.I):
            err(f"астрология / Golden Dawn / стихии: «{t[:60]}»")
        plain = t
        for rx in names:
            plain = rx.sub(" ", plain)
        found = [h.pattern for h in harsh_rx if h.search(plain)
                 and not (pid in LEGAL and h.pattern.replace("(?<!\\w)", "").replace("(?!\\w)", "") in LEGAL_HARSH_OK)]
        if found:
            err(f"тяжёлые слова {found}: «{t[:60]}»")
        if re.search(r"\b(100 ?%|100 percent|100 por ciento|accurate reading|certer[oa] al 100)", t, re.I):
            err(f"обещание точности: «{t[:60]}»")
        if lang == "es":
            if re.search(r"\busted(es)?\b", t, re.I):
                err(f"«usted» — только «tú»: «{t[:60]}»")
            m = cp.ES_GENDER.search(t)
            if m:
                warn(f"проверить род о читателе: «{m.group(0)}» в «{t[:60]}»")
    for t in texts(page) + [b.get("heading", "") for b in blocks] + [h1]:
        if lang == "es" and re.search(r"\binvertid[ao]s?\b", t, re.I):
            err(f"«invertida» — только в title/description: «{t[:60]}»")
    # --- совпадения с другими страницами языка и со страницами карт ---
    mine = cp.shingles(texts(page))
    worst, worst_id = 0.0, ""
    for oid, osh in others.items():
        if oid == f"{lang}/{pid}":
            continue
        o = cp.overlap(mine, osh)
        if o > worst:
            worst, worst_id = o, oid
    if worst > cp.OVERLAP_MAX:
        err(f"совпадения {worst:.1%} с {worst_id} (≤ {cp.OVERLAP_MAX:.0%})")
    summary = f"слов {n} (план {lo}–{hi}), title {len(title)}, description {len(desc)}, интентов {len(intents)}, " \
              f"совпадения ≤ {worst:.1%} ({worst_id})"
    return errs, warns, summary


def shingle_index(lang: str) -> dict[str, set]:
    idx = {}
    for f in sorted((PAGES / lang).glob("*.json")):
        idx[f"{lang}/{f.stem}"] = cp.shingles(texts(json.loads(f.read_text())))
    for f in sorted((CARD_PAGES / lang).glob("*.json")):
        d = json.loads(f.read_text())
        idx[f"cards/{lang}/{f.stem}"] = cp.shingles(cp.prose(d))
    return idx


def main(argv: list[str]) -> int:
    ctx = cp.load_context()
    paths = [Path(a) for a in argv] if argv else sorted(PAGES.glob("*/*.json"))
    index = {lang: shingle_index(lang) for lang in cp.LANGS}
    bad = 0
    for p in paths:
        page = json.loads(Path(p).read_text())
        errs, warns, summary = check(page, str(p), ctx, index.get(page.get("lang"), {}))
        bad += bool(errs)
        print(f"{p}: {'OK' if not errs else f'{len(errs)} ошибок'} — {summary}")
        for e in errs:
            print(f"  ошибка: {e}")
        for w in warns:
            print(f"  предупреждение: {w}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
