"""Проверка страниц карт content/cards/pages/{en,es}/*.json по правилам
docs/research/stage5/30-card-page-rules.md (только стандартная библиотека).

Запуск из корня репозитория:
  python3 -I tools/cards/check_pages.py                    — все страницы
  python3 -I tools/cards/check_pages.py FILE [FILE ...]    — выбранные страницы
Совпадения пятисловных цепочек каждая выбранная страница сравнивает со всеми страницами своего языка.
Код выхода 0 — ошибок нет (предупреждения не мешают), 1 — есть ошибки.
"""
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app.reader.check import find_claims, live_terms, load_reader_terms, word_count  # noqa: E402
from app.terms import load_terms  # noqa: E402

CONTENT = ROOT / "content/cards"
PAGES = CONTENT / "pages"
TEMPLATES = PAGES / "template-strings.json"
WAITE_DIR = ROOT / "content/sources/waite-pictorial-key"
BASE_TERMS = Path(__file__).resolve().parent / "banned_terms.json"

LANGS = ("en", "es")
BLOCK_ORDER = ["on_the_card", "waite", "upright", "reversed", "love", "work_money", "advice", "yes_no",
               "in_a_reading", "combinations", "not_to_confuse", "ask_yourself"]
TOP_FIELDS = {"schema", "card_id", "lang", "status", "editor", "reviewed_at", "name_forms", "title", "description",
              "h1", "image_alt", "facts", "capsule", "keywords", "blocks", "faq", "related", "mentions", "waite",
              "citations", "sources"}
STATUSES = ("draft", "reviewed", "published")
EDITOR_PLACEHOLDER = "{editor_name}"
WIKISOURCE = "https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot"
COMMONS = "https://commons.wikimedia.org/wiki/"

# Объём: текст, который видит читатель, без заголовков и вопросов FAQ (карта + строки шаблона).
WORDS = {"major": (1200, 1650), "minor": (900, 1300)}
# Ориентиры по блокам (только предупреждения): (старшие), (младшие).
BLOCK_WORDS = {
    "on_the_card": ((150, 280), (90, 200)), "waite": ((40, 160), (30, 140)),
    "upright": ((110, 300), (90, 220)), "reversed": ((80, 250), (70, 200)), "love": ((90, 250), (80, 200)),
    "work_money": ((50, 180), (40, 150)), "advice": ((30, 120), (30, 120)), "in_a_reading": ((40, 120), (40, 120)),
    "combinations": ((40, 150), (30, 150)), "not_to_confuse": ((50, 130), (50, 130)),
    "ask_yourself": ((20, 60), (20, 60)), "faq": ((150, 320), (130, 300)),
}
CAPSULE_WORDS = (40, 60)
TITLE_MAX = 60
DESCRIPTION = (130, 160)
QUOTE_MAX_WORDS = 25
FAQ_COUNT = (3, 6)
PAIRS = (3, 4)
RELATED = (3, 6)
SHINGLE = 5
OVERLAP_MAX = 0.03
FAQ_SHARED_MAX = 2  # общих пятисловных цепочек ответа FAQ с блоками страницы

GOOD_BAD = {"en": re.compile(r"\bgood or bad\b", re.I), "es": re.compile(r"\bbuena o mala\b", re.I)}
VERDICT_WORD = {"en": {"yes": r"\byes\b", "no": r"\bno\b", "unclear": r"\bnot clear\b"},
                "es": {"yes": r"\bsí\b", "no": r"\bno\b", "unclear": r"\bno está claro\b"}}
# Тяжёлые старинные слова Уэйта: в цитате — с флагом waite.harsh, в тексте страницы — нельзя.
HARSH = {
    "en": [r"death", r"dead", r"dies?", r"dying", r"miscarriage", r"illness", r"disease", r"sickness",
           r"lawsuits?", r"imprisonment", r"prison", r"madness", r"insanity", r"mental alienation", r"mania",
           r"delirium", r"frenzy", r"widowhood", r"ruin", r"perdition", r"perish", r"calamity", r"catastrophe",
           r"misery", r"tyranny", r"theft", r"treachery", r"sterility"],
    "es": [r"muertes?", r"muert[oa]s?", r"morir\w*", r"aborto", r"enfermedad(es)?", r"pleitos?",
           r"demanda judicial", r"encarcelamiento", r"prisión", r"cárcel", r"enajenación", r"demencia",
           r"manía", r"delirio", r"frenesí", r"viudez", r"ruina", r"perdición", r"perecer", r"calamidad",
           r"catástrofe", r"miseria", r"tiranía", r"robo", r"traición", r"esterilidad"],
}
NO_CORRESPONDENCE = {
    "en": r"Golden Dawn|zodiac|astrolog\w*|\bplanet\w*|\bSaturn\b|\bLibra\b|\belement of (air|fire|water|earth)\b",
    "es": r"Golden Dawn|zod[ií]aco|astrolog\w*|\bplaneta\w*|\bSaturno\b|\bLibra\b|\belemento (aire|fuego|agua|tierra)\b",
}
MODERN_LABEL = {"en": r"\bin modern readings\b", "es": r"\ben las lecturas modernas\b"}
ES_GENDER = re.compile(r"\b(ti|contigo|t[úu]) mism[oa]\b|\bsegur[oa] de ti\b|\b(list[oa] para|cansad[oa]|dispuest[oa]"
                       r"|preparad[oa]|decepcionad[oa]|agobiad[oa]|abrumad[oa]|nervios[oa]|solter[oa])\b", re.I)
STOP = {
    "en": set("what does do is are the a an of in on for and or mean means meaning card tarot it as to with about "
              "how why when cards".split()),
    "es": set("qué que significa significan el la los las de del en es y o u un una carta cartas tarot como al a "
              "con se lo sobre cómo para por".split()),
}
_WORD = re.compile(r"[\w’'-]+")
_PAGE_REF = re.compile(r"\((pp?)\.\s*([^)]*)\)")
_QUOTE_EN = re.compile(r"\"([^\"]+)\"")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Result:
    path: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def waite_pages(folder: Path = WAITE_DIR) -> dict[int, str]:
    """{номер страницы: текст}; метка [p. N] стоит перед текстом страницы N."""
    pages = {}
    for name in ("preface.txt", "part-1.txt", "part-2.txt", "part-3.txt"):
        path = folder / name
        if not path.exists():
            continue
        parts = re.split(r"\[p\. (\d+)\]", path.read_text(encoding="utf-8"))
        for i in range(1, len(parts), 2):
            pages[int(parts[i])] = pages.get(int(parts[i]), "") + parts[i + 1]
    return pages


def squash(text: str) -> str:
    """Для сверки цитат: без пробелов и переносов, прямые кавычки, без учёта регистра."""
    text = text.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}))
    return re.sub(r"\s+", "", text).lower()


def in_source(text: str, pages: list[int], source: dict[int, str]) -> bool:
    """Фрагменты, разделённые «…», стоят на указанных страницах дословно и по порядку."""
    if not pages or any(p not in source for p in pages):
        return False
    haystack = squash("".join(source[p] for p in sorted(pages)))
    pos = 0
    for piece in re.split(r"…|\.\.\.", text):
        piece = squash(piece).strip(".,;:")
        if not piece:
            continue
        found = haystack.find(piece, pos)
        if found < 0:
            return False
        pos = found + len(piece)
    return True


def page_refs(text: str) -> list[tuple[int, int]]:
    """«(p. 152)», «(pp. 29–30)», «(pp. 152, 161)» → [(152, 152)], [(29, 30)], [(152, 152), (161, 161)]."""
    refs = []
    for m in _PAGE_REF.finditer(text):
        for part in re.split(r",|\band\b|\by\b", m.group(2)):
            nums = [int(n) for n in re.findall(r"\d+", part)]
            if len(nums) == 1:
                refs.append((nums[0], nums[0]))
            elif len(nums) == 2:
                refs.append((nums[0], nums[1]))
    return refs


def words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def shingles(texts: list[str], n: int = SHINGLE) -> set:
    out = set()
    for text in texts:
        w = words(text)
        out |= {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}
    return out


def overlap(a: set, b: set) -> float:
    """Доля общих пятисловных цепочек от меньшей страницы."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def block(page: dict, block_id: str) -> dict:
    return next((b for b in page.get("blocks", []) if b.get("id") == block_id), {})


def prose(page: dict) -> list[str]:
    """Текст карты, который видит читатель: капсула, абзацы, пары, ответы FAQ (без цитаты Уэйта)."""
    texts = [page.get("capsule", "")]
    for b in page.get("blocks", []):
        texts += b.get("paragraphs", [])
        texts += [p.get("text", "") for p in b.get("pairs", [])]
    texts += [f.get("a", "") for f in page.get("faq", [])]
    return [t for t in texts if t]


def headings(page: dict) -> list[str]:
    return [b.get("heading", "") for b in page.get("blocks", [])]


def all_units(page: dict) -> list[str]:
    """Всё, что пишет автор карты, кроме дословной цитаты Уэйта и её перевода."""
    units = [page.get(k, "") for k in ("title", "description", "h1", "image_alt")]
    units += headings(page) + prose(page) + [f.get("q", "") for f in page.get("faq", [])]
    return [u for u in units if u]


def template_leaves(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in template_leaves(v)]
    if isinstance(node, list):
        return [s for v in node for s in template_leaves(v)]
    return []


def rendered_template(page: dict, tpl: dict, reason: str) -> list[str]:
    """Строки шаблона, которые этап 6 выводит в тексте этой страницы (для подсчёта объёма)."""
    t = tpl[page["lang"]]
    texts = [t["waite"]["boundary"], t["work_money"]["money_line"], t["yes_no"]["upright"], t["yes_no"]["reversed"],
             t["yes_no"]["rule"], reason, t["in_a_reading"]["note"], t["combinations"]["intro"], t["cta"]["text"],
             t["about"]["method"], t["about"]["deck_note"], t["about"]["page_numbers"]]
    if (page.get("waite") or {}).get("harsh"):
        texts.append(t["waite"]["harsh_context"])
    return texts


def name_patterns(meanings: dict[str, dict], lang: str) -> dict[str, re.Pattern]:
    """Имя карты в тексте: «The Magician», «the Magician», «El Mago», «Ace of Wands» (с заглавной)."""
    out = {}
    for card_id, m in meanings.items():
        core = re.sub(r"^(The|El|La|Los|Las)\s+", "", m["name"])
        out[card_id] = re.compile(r"(?<![\w-])" + re.escape(core) + r"(?![\w-])")
    return out


@dataclass
class Context:
    deck: dict
    meanings: dict  # lang -> card_id -> entry
    rules: dict
    sources: dict
    templates: dict
    source_pages: dict
    reader_terms: dict
    base_terms: dict
    names: dict  # lang -> card_id -> pattern


def load_context() -> Context:
    meanings = {lang: {m["card_id"]: m for m in load_json(CONTENT / f"meanings.{lang}.json")} for lang in LANGS}
    return Context(
        deck={c["card_id"]: c for c in load_json(CONTENT / "deck.json")},
        meanings=meanings,
        rules=load_json(CONTENT / "yes-no-rules.json"),
        sources={s["card_id"]: s for s in load_json(CONTENT / "sources.json")},
        templates=load_json(TEMPLATES),
        source_pages=waite_pages(),
        reader_terms=load_reader_terms(),
        base_terms=load_terms(BASE_TERMS),
        names={lang: name_patterns(meanings[lang], lang) for lang in LANGS},
    )


def content_words(text: str, lang: str, name_tokens: set) -> set:
    return {w for w in words(text) if w not in STOP[lang] and w not in name_tokens}


def check_templates(tpl: dict, ctx: Context) -> list[str]:
    errors = []

    def keys(node, prefix=""):
        if isinstance(node, dict):
            return {k2 for k, v in node.items() for k2 in keys(v, f"{prefix}{k}.")} | {prefix}
        return {prefix}

    if set(tpl) - {"version", "description"} != set(LANGS):
        errors.append("template-strings.json: нужны ключи en и es")
        return errors
    if keys(tpl["en"]) != keys(tpl["es"]):
        errors.append(f"template-strings.json: разные ключи en/es: {sorted(keys(tpl['en']) ^ keys(tpl['es']))}")
    for lang in LANGS:
        method = tpl[lang].get("about", {}).get("method", "")
        if "{editor_name}" not in method or "{reviewed_at}" not in method:
            errors.append(f"template-strings.json {lang}: about.method без {{editor_name}} / {{reviewed_at}}")
        terms = live_terms(ctx.reader_terms, lang)
        for text in template_leaves(tpl[lang]):
            hits = find_claims(text, terms, lang)[0] + [t for t, rx in ctx.base_terms[lang] if rx.search(text)]
            if hits:
                errors.append(f"template-strings.json {lang}: запрещённые слова {hits} в «{text[:60]}»")
    return errors


def check_page(page: dict, ctx: Context, path: str = "") -> Result:
    r = Result(path or f"{page.get('lang')}/{page.get('card_id')}")
    err, warn = r.errors.append, r.warnings.append

    missing = TOP_FIELDS - set(page)
    extra = set(page) - TOP_FIELDS
    if missing:
        err(f"нет полей: {sorted(missing)}")
        return r
    if extra:
        err(f"лишние поля: {sorted(extra)}")
    lang, card_id = page["lang"], page["card_id"]
    if lang not in LANGS or card_id not in ctx.deck:
        err(f"неизвестные lang/card_id: {lang} / {card_id}")
        return r
    deck, meaning = ctx.deck[card_id], ctx.meanings[lang][card_id]
    tpl = ctx.templates[lang]
    if path and Path(path).stem != card_id:
        err(f"имя файла не совпадает с card_id {card_id}")
    if path and Path(path).parent.name != lang:
        err(f"файл лежит не в папке своего языка ({lang})")
    if page["schema"] != 2:
        err("schema должна быть 2")

    # --- статус, редактор, дата проверки ---
    if page["status"] not in STATUSES:
        err(f"status: {page['status']!r}, допустимо {STATUSES}")
    if not isinstance(page["editor"], str) or not page["editor"].strip():
        err("editor: пустой")
    if page["reviewed_at"] is not None:
        if not (isinstance(page["reviewed_at"], str) and _ISO.match(page["reviewed_at"])):
            err("reviewed_at: null или дата YYYY-MM-DD")
        else:
            try:
                date.fromisoformat(page["reviewed_at"])
            except ValueError:
                err("reviewed_at: несуществующая дата")
    if page["status"] == "published" and (page["reviewed_at"] is None or page["editor"] == EDITOR_PLACEHOLDER):
        err("published без reviewed_at или с заглушкой {editor_name}")

    # --- имя, факты ---
    names = page["name_forms"]
    need = {"name", "in_sentence"} | ({"de"} if lang == "es" else set())
    if not isinstance(names, dict) or set(names) != need:
        err(f"name_forms: нужны ключи {sorted(need)}")
        names = {"name": meaning["name"], "in_sentence": meaning["name"], "de": meaning["name"]}
    if names["name"] != meaning["name"]:
        err(f"name_forms.name {names['name']!r} ≠ имени в meanings.{lang}.json {meaning['name']!r}")
    if names["in_sentence"].lower() not in (meaning["name"].lower(), ("the " if lang == "en" else "el ")
                                           + meaning["name"].lower()):
        err(f"name_forms.in_sentence: {names['in_sentence']!r}")
    name_tokens = set(words(" ".join(names.values())))
    facts = page["facts"]
    for key in ("arcana", "suit", "number", "numeral"):
        if facts.get(key) != deck[key]:
            err(f"facts.{key}: {facts.get(key)!r} ≠ deck.json {deck[key]!r}")
    if set(facts) != {"arcana", "suit", "number", "numeral", "also_called"}:
        err("facts: ключи arcana, suit, number, numeral, also_called (соответствий Golden Dawn нет — решение 3)")

    # --- title, description, h1, alt ---
    title, desc, h1 = page["title"], page["description"], page["h1"]
    r.stats.update(title=len(title), description=len(desc))
    if len(title) > TITLE_MAX:
        err(f"title {len(title)} знаков > {TITLE_MAX}: нужна резервная формула")
    if not title.startswith(names["name"]):
        err("title начинается не с имени карты")
    if not DESCRIPTION[0] <= len(desc) <= DESCRIPTION[1]:
        err(f"description {len(desc)} знаков, нужно {DESCRIPTION[0]}–{DESCRIPTION[1]}")
    if not h1.startswith(names["name"]) or len(h1) >= len(title):
        err("h1: начинается с имени карты и короче title")
    if not page["image_alt"] or len(page["image_alt"]) > 250:
        err("image_alt: от 1 до 250 знаков")

    # --- капсула и ключевые слова ---
    cap_words = word_count(page["capsule"])
    if not CAPSULE_WORDS[0] <= cap_words <= CAPSULE_WORDS[1]:
        err(f"capsule {cap_words} слов, нужно {CAPSULE_WORDS[0]}–{CAPSULE_WORDS[1]}")
    if not re.search(VERDICT_WORD[lang][deck["yes_no"]], page["capsule"], re.I):
        err(f"capsule: нет вердикта «{deck['yes_no']}» из deck.json")
    kws = page["keywords"]
    if kws.get("upright", []) + kws.get("reversed", []) != meaning["keywords"] + kws.get("reversed", []) or \
            kws.get("upright") != meaning["keywords"]:
        err(f"keywords.upright ≠ meanings.{lang}.json keywords")
    if not 3 <= len(kws.get("reversed", [])) <= 5:
        err("keywords.reversed: 3–5 слов")
    body_text = " ".join(prose(page)).lower()
    for kw in kws.get("upright", []) + kws.get("reversed", []):
        if kw.lower() not in body_text:
            err(f"ключевое слово «{kw}» не встречается в тексте страницы")

    # --- блоки ---
    ids = [b.get("id") for b in page["blocks"]]
    if ids != BLOCK_ORDER:
        err(f"блоки и порядок: {ids}, нужно {BLOCK_ORDER}")
    arc = 0 if deck["arcana"] == "major" else 1
    for b in page["blocks"]:
        bid, heading = b.get("id"), b.get("heading", "")
        if bid == "combinations":
            if "paragraphs" in b:
                err("combinations: только pairs, без paragraphs (вводная — строка шаблона)")
        elif not isinstance(b.get("paragraphs"), list):
            err(f"{bid}: нет paragraphs")
        name_in = names["name"].lower() in heading.lower() or names["in_sentence"].lower() in heading.lower()
        if not name_in:
            err(f"заголовок {bid} без имени карты: «{heading}»")
        if lang == "es" and not (heading.startswith("¿") and heading.endswith("?")):
            err(f"заголовок {bid} в ES — вопрос «¿…?»: «{heading}»")
        if bid in BLOCK_WORDS:
            low, high = BLOCK_WORDS[bid][arc]
            n = sum(word_count(t) for t in b.get("paragraphs", []) + [p.get("text", "") for p in b.get("pairs", [])])
            if not low <= n <= high:
                warn(f"{bid}: {n} слов, ориентир {low}–{high}")
    if block(page, "yes_no").get("paragraphs"):
        err("yes_no: абзацы не пишутся — блок собирается из deck.json, yes-no-rules.json и yes_no_why")
    pairs = block(page, "combinations").get("pairs", [])
    if not PAIRS[0] <= len(pairs) <= PAIRS[1]:
        err(f"combinations: {len(pairs)} пар, нужно {PAIRS[0]}–{PAIRS[1]}")
    for p in pairs:
        if p.get("card_id") not in ctx.deck or p.get("card_id") == card_id or not p.get("text"):
            err(f"combinations: плохая пара {p}")
    if len(block(page, "ask_yourself").get("paragraphs", [])) != 3:
        err("ask_yourself: ровно 3 вопроса")

    # --- FAQ ---
    faq = page["faq"]
    if not FAQ_COUNT[0] <= len(faq) <= FAQ_COUNT[1]:
        err(f"faq: {len(faq)} вопросов, нужно {FAQ_COUNT[0]}–{FAQ_COUNT[1]}")
    if not any(GOOD_BAD[lang].search(f.get("q", "")) for f in faq):
        err("faq: нет обязательного вопроса «good or bad» / «buena o mala»")
    heading_sets = [(h, content_words(h, lang, name_tokens)) for h in headings(page)]
    block_shingles = shingles([t for b in page["blocks"] for t in b.get("paragraphs", [])] + [page["capsule"]])
    faq_words = 0
    for f in faq:
        q, a = f.get("q", ""), f.get("a", "")
        faq_words += word_count(a)
        if lang == "es" and not (q.startswith("¿") and q.endswith("?")):
            err(f"faq ES: вопрос «¿…?»: «{q}»")
        qc = content_words(q, lang, name_tokens)
        for h, hc in heading_sets:
            if qc and hc and hc <= qc and not (qc - hc):
                err(f"faq повторяет заголовок блока: «{q}» ≈ «{h}»")
        shared = len(shingles([a]) & block_shingles)
        if shared > FAQ_SHARED_MAX:
            err(f"faq: ответ на «{q}» повторяет фразы блоков ({shared} общих пятисловных цепочек)")
    low, high = BLOCK_WORDS["faq"][arc]
    if not low <= faq_words <= high:
        warn(f"faq: {faq_words} слов в ответах, ориентир {low}–{high}")

    # --- связи ---
    related = page["related"]
    if not RELATED[0] <= len(related) <= RELATED[1] or any(c not in ctx.deck or c == card_id for c in related):
        err(f"related: {RELATED[0]}–{RELATED[1]} других карт из deck.json")
    mentions = page["mentions"]
    mention_ids = set()
    for m in mentions:
        if m.get("card_id") not in ctx.deck or m.get("card_id") == card_id:
            err(f"mentions: неизвестная карта {m}")
            continue
        mention_ids.add(m["card_id"])
        if m.get("text", "\0") not in " ".join(prose(page)):
            err(f"mentions: «{m.get('text')}» нет в тексте")
    pair_ids = {p.get("card_id") for p in pairs}
    for other, rx in ctx.names[lang].items():
        if other == card_id:
            continue
        hit = any(rx.search(t) for t in prose(page) if t not in [p.get("text") for p in pairs])
        if hit and other not in mention_ids:
            err(f"в тексте упомянута карта {other} — добавить в mentions (ссылка)")
        if not hit and other in mention_ids and other not in pair_ids:
            err(f"mentions: {other} нет в тексте")

    # --- Уэйт: цитата, перевод, тяжёлые слова ---
    w = page["waite"]
    if set(w) != {"quote", "quote_lang", "pages", "translation", "harsh"}:
        err("waite: ключи quote, quote_lang, pages, translation, harsh")
    quote = w.get("quote", "")
    if word_count(quote) > QUOTE_MAX_WORDS:
        err(f"waite.quote: {word_count(quote)} слов > {QUOTE_MAX_WORDS}")
    if re.match(r"\s*Divinatory Meanings", quote):
        err("waite.quote: без рубрики «Divinatory Meanings:»")
    if w.get("quote_lang") != "en":
        err("waite.quote_lang: \"en\" (цитата всегда в оригинале)")
    if not in_source(quote, w.get("pages", []), ctx.source_pages):
        err(f"waite.quote не найдена дословно на стр. {w.get('pages')}")
    if lang == "es" and not w.get("translation"):
        err("waite.translation: в ES нужен полный перевод цитаты («traducción nuestra»)")
    if lang == "en" and w.get("translation") is not None:
        err("waite.translation: в EN — null")
    harsh_rx = [re.compile(r"(?<!\w)" + h + r"(?!\w)", re.I) for h in HARSH[lang]]
    harsh_en = [re.compile(r"(?<!\w)" + h + r"(?!\w)", re.I) for h in HARSH["en"]]
    in_quote = any(rx.search(quote) for rx in harsh_en) or any(rx.search(w.get("translation") or "")
                                                               for rx in harsh_rx)
    if in_quote and not w.get("harsh"):
        err("waite.harsh: в цитате тяжёлые слова — нужно true (шаблон добавит строку контекста)")
    if w.get("harsh") and not in_quote:
        warn("waite.harsh: true, но тяжёлых слов в цитате не найдено")
    all_names = [n for n in ctx.names[lang].values()]
    for text in all_units(page):
        plain = text
        for rx in all_names:
            plain = rx.sub(" ", plain)
        found = [h.pattern for h in harsh_rx if h.search(plain)]
        if found:
            err(f"тяжёлые слова вне цитаты Уэйта {found}: «{text[:70]}»")

    # --- ссылки на страницы и цитаты ---
    cited = set(w.get("pages", []))
    for c in page["citations"]:
        if not in_source(c.get("text", ""), c.get("pages", []), ctx.source_pages):
            err(f"citations: «{c.get('text', '')[:60]}» нет дословно на стр. {c.get('pages')}")
        cited |= set(c.get("pages", []))
    for text in all_units(page):
        for start, end in page_refs(text):
            if start not in cited or end not in cited:
                err(f"ссылка на стр. {start}–{end} без записи в citations: «{text[:60]}»")
    if lang == "en":
        cit_text = [squash(c.get("text", "")) for c in page["citations"]]
        for text in prose(page):
            for frag in _QUOTE_EN.findall(text):
                if word_count(frag) >= 3 and not any(squash(frag).strip(".,;:") in c for c in cit_text):
                    err(f"цитата «{frag[:50]}» не выписана в citations")

    # --- источники ---
    kinds = {s.get("kind"): s for s in page["sources"]}
    if set(kinds) != {"image", "waite", "project"} or len(page["sources"]) != 3:
        err("sources: по одному image, waite, project")
    else:
        commons = COMMONS + ctx.sources[card_id]["commons_title"].replace(" ", "_")
        if kinds["image"].get("url") != commons:
            err(f"sources image.url: {commons}")
        if kinds["waite"].get("url") != WIKISOURCE:
            err(f"sources waite.url: {WIKISOURCE}")
        if sorted(kinds["waite"].get("pages", [])) != sorted(cited):
            err(f"sources waite.pages {kinds['waite'].get('pages')} ≠ страницы цитат {sorted(cited)}")
        for s in page["sources"]:
            if not s.get("what") or not s.get("where") or "url" not in s:
                err(f"sources: нужны what, where, url ({s.get('kind')})")

    # --- запреты сайта, шаблонные строки, испанский ---
    terms = live_terms(ctx.reader_terms, lang)
    for text in all_units(page):
        hits, _ = find_claims(text, terms, lang)
        hits += [t for t, rx in ctx.base_terms[lang] if rx.search(text)]
        if hits:
            err(f"запрещённые слова {sorted(set(hits))}: «{text[:70]}»")
        if re.search(NO_CORRESPONDENCE[lang], text, re.I):
            err(f"соответствия Golden Dawn / астрология — не публикуем (решение 3): «{text[:60]}»")
    joined = " ".join(all_units(page))
    for leaf in template_leaves(tpl):
        for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\{\w+\}", "", leaf)):
            if word_count(sentence) >= 6 and sentence.strip() in joined:
                err(f"строка шаблона в тексте карты: «{sentence[:60]}»")
    if len(re.findall(MODERN_LABEL[lang], joined, re.I)) > 1:
        warn("метка «modern readings» больше одного раза — граница стоит в конце блока waite")
    if lang == "es":
        for text in all_units(page):
            is_meta = text in (title, desc)
            if re.search(re.escape(names["name"]) + r"\s+(al derecho\s+e\s+)?(invertid|derech)", text, re.I):
                err(f"«invertida/derecha» сразу после имени карты: «{text[:60]}»")
            if re.search(r"al derecho e invertid", text, re.I):
                err(f"«al derecho e invertida» — писать «al derecho y al revés (carta invertida)»: «{text[:60]}»")
            if not is_meta and re.search(r"(?<!carta )(?<!cartas )\binvertid[ao]s?\b", text, re.I):
                err(f"«invertida» в тексте страницы — только «al revés»: «{text[:60]}»")
            if re.search(r"\busted(es)?\b", text, re.I):
                err(f"«usted» — только «tú»: «{text[:60]}»")
            for m in ES_GENDER.finditer(text):
                warn(f"проверить род о читателе: «{m.group(0)}» в «{text[:50]}»")

    # --- объём ---
    card_words = sum(word_count(t) for t in prose(page)) + word_count(quote) + word_count(w.get("translation") or "")
    tpl_words = sum(word_count(t) for t in rendered_template(page, ctx.templates, meaning["yes_no_why"]))
    total = card_words + tpl_words
    low, high = WORDS[deck["arcana"]]
    r.stats.update(card_words=card_words, words=total)
    if not low <= total <= high:
        err(f"объём {total} слов (текст карты {card_words} + шаблон {tpl_words}), нужно {low}–{high}")
    return r


def page_files() -> list[Path]:
    return sorted(p for lang in LANGS for p in (PAGES / lang).glob("*.json"))


def run(paths: list[Path], ctx: Context) -> list[Result]:
    results = []
    everything = {p.resolve(): load_json(p) for p in page_files()}
    for path in paths:
        page = everything.get(path.resolve()) or load_json(path)
        everything[path.resolve()] = page
        try:
            rel = str(path.resolve().relative_to(ROOT))
        except ValueError:
            rel = str(path)
        try:
            res = check_page(page, ctx, rel)
        except (KeyError, TypeError, AttributeError) as e:
            res = Result(rel, errors=[f"структура файла: {type(e).__name__}: {e}"])
        mine = shingles(prose(page))
        worst = (0.0, "")
        for other_path, other in everything.items():
            if other_path == path.resolve() or other.get("lang") != page.get("lang"):
                continue
            share = overlap(mine, shingles(prose(other)))
            if share > worst[0]:
                worst = (share, other.get("card_id", other_path.name))
            if share > OVERLAP_MAX:
                res.errors.append(f"совпадение пятисловных цепочек с {other.get('card_id')}: {share:.1%} > 3 %")
        res.stats["overlap"] = worst
        results.append(res)
    return results


def main(argv: list[str]) -> int:
    ctx = load_context()
    paths = [Path(a) for a in argv] if argv else page_files()
    failed = False
    for err in check_templates(ctx.templates, ctx):
        print(err)
        failed = True
    for res in run(paths, ctx):
        s = res.stats
        share, other = s.get("overlap", (0.0, ""))
        status = "OK" if not res.errors else f"{len(res.errors)} ошибок"
        print(f"{res.path}: {status} — слов {s.get('words', '?')} (текст карты {s.get('card_words', '?')}), "
              f"title {s.get('title', '?')}, description {s.get('description', '?')}, "
              f"совпадения ≤ {share:.1%}{' (' + other + ')' if other else ''}")
        for e in res.errors:
            print(f"  ошибка: {e}")
        for wmsg in res.warnings:
            print(f"  предупреждение: {wmsg}")
        failed = failed or bool(res.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
