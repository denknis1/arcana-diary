import copy

import pytest

import check_pages as cp

CTX = cp.load_context()
FILES = cp.page_files()
PAGES = {(p.parent.name, p.stem): cp.load_json(p) for p in FILES}


def page(lang="en", card="major-00-fool"):
    return copy.deepcopy(PAGES[(lang, card)])


def errors(p):
    return cp.check_page(p, CTX).errors


def blk(p, block_id):
    return cp.block(p, block_id)


def has(errs, text):
    return any(text in e for e in errs)


# --- образцы проходят ---

@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_sample_pages_pass(path):
    res = cp.run([path], CTX)[0]
    assert res.errors == []


def test_templates_pass():
    assert cp.check_templates(CTX.templates, CTX) == []


def test_main_exit_code_ok():
    assert cp.main([str(p) for p in FILES]) == 0


# --- источник: цитаты и страницы ---

def test_quote_must_be_verbatim():
    p = page()
    p["waite"]["quote"] = p["waite"]["quote"].replace("Folly", "Foolishness")
    assert has(errors(p), "waite.quote не найдена")


def test_quote_wrong_page():
    p = page()
    p["waite"]["pages"] = [152]
    assert has(errors(p), "waite.quote не найдена")


def test_quote_across_page_break_and_ellipsis():
    src = CTX.source_pages
    assert cp.in_source("is attacking him from behind", [29, 30], src)
    assert cp.in_source("by considering the general trend of the cards", [309, 310], src)
    assert cp.in_source("Removal, absence … Reversed: Mental alienation", [248], src)
    assert not cp.in_source("Reversed: Mental alienation … Removal, absence", [248], src)


def test_citation_not_in_source():
    p = page()
    p["citations"][0]["text"] = "with heavy step"
    assert has(errors(p), "citations:")


def test_page_reference_needs_citation():
    p = page()
    blk(p, "upright")["paragraphs"][0] += " Waite says so (p. 99)."
    assert has(errors(p), "ссылка на стр. 99")


def test_unlisted_english_quote():
    p = page()
    blk(p, "upright")["paragraphs"][0] += ' Waite calls him "a prince of the other world" here.'
    assert has(errors(p), "не выписана в citations")


def test_page_refs_parsing():
    assert cp.page_refs("x (pp. 29–30) y (p. 152) z (pp. 152, 161 y 196)") == [
        (29, 30), (152, 152), (152, 152), (161, 161), (196, 196)]


def test_sources_pages_follow_citations():
    p = page()
    p["sources"][1]["pages"] = [152]
    assert has(errors(p), "sources waite.pages")


# --- тяжёлые слова Уэйта ---

def test_harsh_quote_needs_flag():
    p = page("en", "swords-03-three")
    p["waite"]["harsh"] = False
    assert has(errors(p), "waite.harsh")


def test_harsh_flag_without_harsh_words_is_error():
    p = page("en", "swords-03-three")
    p["waite"]["quote"] = "Removal, absence, delay"
    assert has(errors(p), "нужно false")


def test_flag_word_sets_harsh_but_is_allowed_in_text():
    p = page()
    p["waite"]["harsh"] = False
    p["waite"]["quote"] = "Folly, mania, extravagance, intoxication, delirium, frenzy, bewrayment"
    assert has(errors(p), "нужно true")
    q = page()
    blk(q, "upright")["paragraphs"][0] += " It is not about danger or legal matters."
    assert not has(errors(q), "тяжёлые слова")


def test_hard_meanings_may_be_named_but_health_may_not():
    p = page()
    blk(p, "upright")["paragraphs"][0] += " Death rarely means physical death; ruin and betrayal are themes, not fate."
    p["mentions"].append({"card_id": "major-13-death", "text": "Death"})
    assert not has(errors(p), "тяжёлые слова")
    blk(p, "upright")["paragraphs"][0] += " It can mean illness."
    assert has(errors(p), "тяжёлые слова")


def test_harsh_word_outside_quote():
    p = page("en", "swords-03-three")
    blk(p, "waite")["paragraphs"][0] += " Waite even lists mental alienation."
    assert has(errors(p), "тяжёлые слова вне цитаты")


def test_card_name_is_not_a_harsh_word():
    p = page()
    blk(p, "upright")["paragraphs"][0] += " It is not Death."
    p["mentions"].append({"card_id": "major-13-death", "text": "Death"})
    assert not has(errors(p), "тяжёлые слова")


def test_es_needs_translation():
    p = page("es")
    p["waite"]["translation"] = None
    assert has(errors(p), "waite.translation")


# --- запреты сайта и решения владельца ---

def test_banned_claim():
    p = page()
    blk(p, "love")["paragraphs"][0] += " He feels the same way."
    assert has(errors(p), "запрещённые слова")


def test_golden_dawn_line_is_rejected():
    p = page()
    blk(p, "on_the_card")["paragraphs"].append("In the Golden Dawn tradition The Fool is linked to Air.")
    assert has(errors(p), "Golden Dawn")


def test_template_string_must_not_be_in_card():
    p = page()
    blk(p, "in_a_reading")["paragraphs"].append(CTX.templates["en"]["in_a_reading"]["note"])
    assert has(errors(p), "строка шаблона")


def test_yes_no_block_has_no_paragraphs():
    p = page()
    blk(p, "yes_no")["paragraphs"] = ["Upright: Yes."]
    assert has(errors(p), "yes_no")


def test_published_needs_editor_and_date():
    p = page()
    p["status"] = "published"
    assert has(errors(p), "published")
    p["editor"], p["reviewed_at"] = "Editor Name", "2026-12-01"
    assert not has(errors(p), "published")


def test_es_invertida_after_name():
    p = page("es")
    p["description"] = "Qué significa El Loco al derecho e invertida: amor, trabajo y consejo. Palabras de Waite (1911), la carta de 1909 y si es sí o no. Sácala ya."
    errs = errors(p)
    assert has(errs, "сразу после имени") and has(errs, "al derecho e invertida")


def test_es_invertida_in_body():
    p = page("es")
    blk(p, "reversed")["paragraphs"][0] += " La carta sale invertida a veces."
    assert has(errors(p), "только «al revés»")


def test_es_heading_is_question():
    p = page("es", "swords-03-three")
    blk(p, "love")["heading"] = "El Tres de Espadas en el amor"
    assert has(errors(p), "вопрос «¿…?»")


# --- заголовки, FAQ, ключевые слова, связи ---

def test_heading_needs_card_name():
    p = page("es", "swords-03-three")
    blk(p, "work_money")["heading"] = "¿Qué significa en el trabajo y el dinero?"
    assert has(errors(p), "без имени карты")


def test_faq_duplicating_heading():
    p = page("es")
    p["faq"].append({"q": "¿Qué significa El Loco en el amor?", "a": "Una respuesta nueva y corta sobre otra cosa."})
    assert has(errors(p), "faq повторяет заголовок")


def test_faq_needs_good_or_bad():
    p = page()
    p["faq"] = [f for f in p["faq"] if "good or bad" not in f["q"]]
    assert has(errors(p), "good or bad")


def test_faq_answer_repeating_block():
    p = page()
    p["faq"][1]["a"] = blk(p, "advice")["paragraphs"][0]
    assert has(errors(p), "повторяет фразы блоков")


def test_keyword_must_appear():
    p = page("en", "swords-03-three")
    para = blk(p, "upright")["paragraphs"]
    para[1] = para[1].replace("release", "letting go")
    assert has(errors(p), "«release»")


def test_unlisted_card_mention():
    p = page()
    blk(p, "upright")["paragraphs"][0] += " It is lighter than The Tower."
    assert has(errors(p), "major-16-tower")


def test_facts_follow_deck():
    p = page()
    p["facts"]["number"] = 22
    assert has(errors(p), "facts.number")


def test_title_too_long():
    p = page("en", "swords-03-three")
    p["title"] = "Three of Swords Tarot Card Meaning: Upright, Reversed & Love!"
    assert has(errors(p), "title 61")


def test_word_limits():
    p = page("en", "swords-03-three")
    blk(p, "upright")["paragraphs"].append("More words about the heart and the rain. " * 20)
    assert has(errors(p), "объём")


# --- совпадения между картами ---

def test_overlap_measure():
    a = cp.shingles(["one two three four five six seven"])
    assert cp.overlap(a, a) == 1.0
    assert cp.overlap(a, cp.shingles(["nothing in common here at all today"])) == 0.0


def test_overlap_between_cards_is_flagged(tmp_path):
    clone = page("en", "swords-03-three")
    fool = page()
    clone["capsule"] = fool["capsule"]
    for b in clone["blocks"]:
        other = blk(fool, b["id"])
        if "paragraphs" in b:
            b["paragraphs"] = other["paragraphs"]
    path = tmp_path / "en" / "swords-03-three.json"
    path.parent.mkdir()
    path.write_text(cp.json.dumps(clone), encoding="utf-8")
    res = cp.run([path], CTX)[0]
    assert has(res.errors, "совпадение пятисловных цепочек с major-00-fool")


def test_feminine_article_and_court_cards():
    p = page("es", "swords-03-three")
    p["name_forms"]["in_sentence"] = "la Tres de Espadas"
    assert not has(errors(p), "name_forms.in_sentence")
    q = page("en", "swords-03-three")
    blk(q, "upright")["paragraphs"][0] += " Waite treats the court cards apart."
    assert not has(errors(q), "запрещённые слова")
    blk(q, "upright")["paragraphs"][0] += " It says nothing about court."
    assert has(errors(q), "запрещённые слова")
