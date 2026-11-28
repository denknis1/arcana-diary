"""tools/site/check_dist.py on small hand-made builds (spec 4.4b §5, §6, §11; stage 6 §8): every page exists, an
indexable page has its head and JSON-LD, no placeholder is left, private and hidden pages are noindex and out of the
sitemap and of every hreflang pair, and the sign-in library is never loaded at start by a reading page."""
import json

import pytest

import check_dist
from check_dist import (EXTRA, READING_PAGES, auth_problems, canonical, dist_file, expected_alternates, expected_pages,
                        head_problems, hidden_link_problems, hidden_pages, indexable_pages, launched_problems, noindex_pages,
                        hreflang_target_problems, list_problems, markup_problems, placeholder_problems, robots_problems,
                        robots_txt_problems, sitemap_problems, static_chunks, unexpected_pages)

ISLAND = '<astro-island component-url="/_astro/ReadingIsland.a1.js" renderer-url="/_astro/client.b2.js"></astro-island>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
LD = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>'
SITE_OTHER = "https://arcanadiary.com/other"
REVIEWED = '<p>Reviewed on <time datetime="2026-11-23">November 23, 2026</time>.</p>'
ROBOTS_TXT = "User-agent: *\nDisallow:\nSitemap: https://arcanadiary.com/sitemap.xml\n"


HIDDEN = {"/about", "/contact", "/privacy", "/terms", "/es/sobre-nosotros", "/es/contacto", "/es/privacidad", "/es/terminos"}


@pytest.fixture
def hidden(monkeypatch):
    """A synthetic state in which the eight service pages are hidden (an operator fact has no value): the rules stay
    protected whatever the real operator.json and facts.json say today."""
    monkeypatch.setattr(check_dist, "hidden_pages", lambda: set(HIDDEN))
    return HIDDEN


def write(dist, name, text):
    file = dist / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def head(path):
    if path in noindex_pages():
        return NOINDEX
    if path in EXTRA:
        return "<title>Not found</title>"
    links = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in sorted(expected_alternates(path)))
    return (f'<title>Title</title><meta name="description" content="About this page">'
            f'<link rel="canonical" href="{canonical(path)}">{links}{LD}')


def sitemap(paths):
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{canonical(p)}</loc></url>" for p in paths) + "</urlset>")


DECK = json.loads((check_dist.SITE / "src/data/deck.json").read_text(encoding="utf-8"))


def links(cards, lang):
    base, key = ("/cards/", "slug_en") if lang == "en" else ("/es/cartas/", "slug_es")
    return "".join(f'<li><a href="{base}{c[key]}">x</a></li>' for c in cards)


def list_pages(dist, drop=None):
    """The pages with card lists, as the build draws them (a nav link to /cards is not a card link)."""
    nav = '<a href="/cards">Cards</a>'
    majors = [c for c in DECK if c["arcana"] == "major"]
    write(dist, "cards.html", head("/cards") + nav + links(DECK, "en"))
    write(dist, "es/cartas.html", head("/es/cartas") + links(DECK, "es"))
    write(dist, "cards/major-arcana.html", head("/cards/major-arcana") + links(majors, "en"))
    write(dist, "es/cartas/arcanos-mayores.html", head("/es/cartas/arcanos-mayores") + links(majors, "es"))
    blocks = "".join(f'<section id="{b}">{links([c for c in DECK if c["yes_no"] == v][:drop], "en")}</section>'
                     for b, v in (("lean-yes", "yes"), ("lean-no", "no"), ("not-clear-yet", "unclear")))
    write(dist, "yes-no/cards.html", head("/yes-no/cards") + nav + blocks)


def site(tmp_path, reading_island='import{x}from"./api.d4.js";'):
    dist = tmp_path / "dist"
    cards = set(check_dist.card_paths("en")) | set(check_dist.card_paths("es"))
    for path in expected_pages():
        write(dist, dist_file(path), head(path) + ISLAND + (REVIEWED if path in cards else ""))
    list_pages(dist)
    write(dist, "_astro/client.b2.js", 'import{h}from"./preact.c3.js";')
    write(dist, "_astro/preact.c3.js", "export const h=1;")
    write(dist, "_astro/ReadingIsland.a1.js", reading_island)
    write(dist, "_astro/api.d4.js", 'const l=()=>import("./supabaseClient.e5.js");export{l};')
    write(dist, "_astro/supabaseClient.e5.js", 'class GoTrueClient{};export{GoTrueClient as A};')
    write(dist, "data/daily-en.json", "[]")
    write(dist, "data/daily-es.json", "[]")
    write(dist, "sitemap.xml", sitemap(indexable_pages()))
    write(dist, "robots.txt", ROBOTS_TXT)
    write(dist, "sw.js", "self.addEventListener('push', () => {});\n")  # stage 8.1: the reminder's service worker
    return dist


def test_every_page_of_stage_6_is_expected():
    pages = expected_pages()
    assert len(pages) == 187
    assert {"/diary", "/es/diario", "/account", "/es/cuenta", "/cards", "/yes-no/cards", "/es/tiradas/3-cartas",
            "/about", "/how-readings-work", "/es/privacidad"} <= set(pages)


def test_the_open_site_would_refuse_the_eight_hidden_service_pages(tmp_path, hidden):
    assert launched_problems(site(tmp_path)) == [f"hidden page on the open site: {p} (an operator placeholder has no value)" for p in
                                   ("/about", "/contact", "/es/contacto", "/es/privacidad", "/es/sobre-nosotros",
                                    "/es/terminos", "/privacy", "/terms")]


def test_hreflang_follows_mutual_pairs_only():
    assert expected_alternates("/yes-no") == {("en", "https://arcanadiary.com/yes-no"),
                                              ("es", "https://arcanadiary.com/es/si-o-no"),
                                              ("x-default", "https://arcanadiary.com/yes-no")}
    # no mutual pair, no hreflang at all (stage 2 spec §3)
    assert expected_alternates("/one-card") == set()
    assert expected_alternates("/es/tiradas/3-cartas") == set()
    assert canonical("/") == "https://arcanadiary.com/"


def test_a_pair_with_a_hidden_page_is_no_hreflang_pair(monkeypatch, hidden):
    monkeypatch.setattr(check_dist, "pairs", lambda: {"/yes-no": "/es/sobre-nosotros", "/es/sobre-nosotros": "/yes-no"})
    assert expected_alternates("/yes-no") == set()


def test_hidden_pages_are_the_service_pages_with_an_operator_placeholder(tmp_path, monkeypatch):
    data = tmp_path / "src/data"
    (data / "pages/en").mkdir(parents=True)
    (data / "facts.json").write_text(json.dumps({"guest_limit": 3, "operator_name": "Acme"}), encoding="utf-8")

    def page(page_id, url, text):
        body = {"page_id": page_id, "url": url, "title": "T", "description": "D", "h1": "H", "lead": text, "capsule": None,
                "blocks": [], "faq": []}
        (data / "pages/en" / f"{page_id}.json").write_text(json.dumps(body), encoding="utf-8")

    page("about", "/about", "By {operator_name}")                 # service page, every value known: open
    page("contact", "/contact", "Write to {operator_email}")      # service page, a value is missing: hidden
    page("one-card", "/one-card", "{guest_limit} a day {nobody}")  # not a service page: never hidden
    monkeypatch.setattr(check_dist, "SITE", tmp_path)
    check_dist.hidden_pages.cache_clear()
    try:
        assert check_dist.hidden_pages() == {"/contact"}
    finally:
        check_dist.hidden_pages.cache_clear()


def test_the_real_service_pages_are_all_open_today(tmp_path):
    """The real operator facts are filled: no page is hidden, so the open site passes (--launched)."""
    assert hidden_pages() == set()
    dist = site(tmp_path)
    assert launched_problems(dist) == []
    assert check_dist.main(dist, launched=True) == 0


def test_only_the_private_and_hidden_pages_say_noindex(tmp_path):
    dist = site(tmp_path)
    assert robots_problems(dist) == []
    write(dist, "diary.html", ISLAND)
    write(dist, "yes-no.html", NOINDEX + ISLAND)
    assert robots_problems(dist) == ["no noindex meta: site/dist/diary.html", "unexpected noindex meta: site/dist/yes-no.html"]


def test_a_noindex_meta_in_any_spelling_is_unexpected_and_leaves_the_indexable_set(tmp_path):
    dist = site(tmp_path)
    write(dist, "love.html", head("/love") + '<meta name="robots" content="NoIndex">' + ISLAND)
    assert robots_problems(dist) == ["unexpected noindex meta: site/dist/love.html"]
    assert "/love" not in indexable_pages(dist)
    assert sitemap_problems(dist) == ["sitemap.xml lists https://arcanadiary.com/love, not an indexable page"]
    # a private page needs the exact string
    write(dist, "diary.html", '<meta name="robots" content="noindex">' + ISLAND)
    assert "no noindex meta: site/dist/diary.html" in robots_problems(dist)


def test_a_good_build_has_every_head_part(tmp_path):
    assert head_problems(site(tmp_path)) == []


def test_each_missing_or_wrong_head_part_is_named(tmp_path):
    dist = site(tmp_path)
    links = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in sorted(expected_alternates("/cards")))
    write(dist, "cards.html", '<title>T</title><link rel="canonical" href="https://arcanadiary.com/cards/">'
          + links + '<script type="application/ld+json">{oops</script>')
    write(dist, "love.html", "<title> </title>")
    assert head_problems(dist) == [
        "no description: site/dist/cards.html",
        "canonical ['https://arcanadiary.com/cards/'] instead of one https://arcanadiary.com/cards: site/dist/cards.html",
        "JSON-LD does not parse: site/dist/cards.html",
        "no title: site/dist/love.html",
        "no description: site/dist/love.html",
        "canonical None instead of one https://arcanadiary.com/love: site/dist/love.html",
        "hreflang [] instead of [('en', 'https://arcanadiary.com/love'), ('es', 'https://arcanadiary.com/es/amor'), "
        "('x-default', 'https://arcanadiary.com/love')]: site/dist/love.html",
        "no JSON-LD: site/dist/love.html",
    ]


def test_two_canonicals_and_a_body_title_are_reported(tmp_path):
    dist = site(tmp_path)
    page = head("/love")
    write(dist, "love.html", page.replace("<title>Title</title>", f'<link rel="canonical" href="{SITE_OTHER}">')
          + "</head><body><svg><title>x</title></svg>")
    assert head_problems(dist) == [
        "no title: site/dist/love.html",
        f"canonical ['{SITE_OTHER}', 'https://arcanadiary.com/love'] instead of one https://arcanadiary.com/love: site/dist/love.html"]


def test_an_html_file_that_is_not_an_expected_page_is_reported(tmp_path):
    dist = site(tmp_path)
    assert unexpected_pages(dist) == []
    write(dist, "secret.html", "x")
    write(dist, "cards/new.html", "x")
    assert unexpected_pages(dist) == ["unexpected page: site/dist/cards/new.html", "unexpected page: site/dist/secret.html"]


def test_an_hreflang_link_to_a_noindex_or_hidden_page_is_reported(tmp_path, hidden):
    dist = site(tmp_path)
    assert hreflang_target_problems(dist) == []
    link = '<link rel="alternate" hreflang="{}" href="https://arcanadiary.com{}">'
    write(dist, "cards.html", head("/cards") + link.format("es", "/es/diario") + ISLAND)
    write(dist, "es/amor.html", head("/es/amor") + link.format("en", "/about") + ISLAND)
    write(dist, "diary.html", NOINDEX + link.format("es", "/es/404") + ISLAND)
    assert hreflang_target_problems(dist) == [
        "hreflang https://arcanadiary.com/es/diario is not an indexable page: site/dist/cards.html",
        "hreflang https://arcanadiary.com/es/404 is not an indexable page: site/dist/diary.html",
        "hreflang https://arcanadiary.com/about is not an indexable page: site/dist/es/amor.html",
    ]


def test_a_placeholder_left_in_the_text_is_reported_but_not_one_inside_a_script(tmp_path):
    dist = site(tmp_path)
    assert placeholder_problems(dist) == []
    write(dist, "love.html", head("/love") + "<p>Draw {guest_limit} a day</p><script>const a = {x};</script>")
    assert placeholder_problems(dist) == ["placeholder {guest_limit} left: site/dist/love.html"]


def test_a_placeholder_inside_json_ld_is_reported(tmp_path):
    dist = site(tmp_path)
    ld = '<script type="application/ld+json">{"description":"{guest_limit} a day"}</script>'
    write(dist, "love.html", head("/love").replace(LD, ld) + ISLAND)
    assert placeholder_problems(dist) == ["placeholder {guest_limit} left in JSON-LD: site/dist/love.html"]
    write(dist, "love.html", head("/love").replace(LD, LD + "<p>{limit_2}</p>") + ISLAND)
    assert placeholder_problems(dist) == ["placeholder {limit_2} left: site/dist/love.html"]


def test_a_malformed_sitemap_is_reported(tmp_path):
    dist = site(tmp_path)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    good = [canonical(p) for p in indexable_pages()]
    url = lambda u: f"<url><loc>{u}</loc></url>"
    body = "".join(url(u) for u in good)
    write(dist, "sitemap.xml", "<urlset")
    assert sitemap_problems(dist)[0].startswith("sitemap.xml is not well-formed XML")
    write(dist, "sitemap.xml", f"<urlset>{body}</urlset>")
    assert sitemap_problems(dist)[0].startswith("sitemap.xml root is urlset")
    write(dist, "sitemap.xml", f'<urlset xmlns="{ns}">{body}{url(good[0])}</urlset>')
    assert sitemap_problems(dist) == [f"sitemap.xml lists {good[0]} twice"]
    link = '<xhtml:link xmlns:xhtml="http://www.w3.org/1999/xhtml" rel="alternate" hreflang="es" href="x"/>'
    write(dist, "sitemap.xml", f'<urlset xmlns="{ns}">{body}<url><loc>{canonical("/love")}</loc>{link}</url></urlset>'
          .replace(url(canonical("/love")), "", 1))
    assert any("exactly one <loc>" in p for p in sitemap_problems(dist))
    write(dist, "sitemap.xml", f'<urlset xmlns="{ns}">{body}<url><loc>{good[0]}</loc><loc>{good[1]}</loc></url></urlset>')
    assert any("exactly one <loc>" in p for p in sitemap_problems(dist))


def test_the_sitemap_lists_exactly_the_indexable_pages(tmp_path, hidden):
    dist = site(tmp_path)
    assert sitemap_problems(dist) == []
    write(dist, "sitemap.xml", sitemap([p for p in indexable_pages() if p != "/cards"] + ["/diary", "/about"]))
    assert sitemap_problems(dist) == ["sitemap.xml lacks https://arcanadiary.com/cards",
                                      "sitemap.xml lists https://arcanadiary.com/about, not an indexable page",
                                      "sitemap.xml lists https://arcanadiary.com/diary, not an indexable page"]


def test_robots_txt_names_the_sitemap(tmp_path):
    dist = site(tmp_path)
    assert robots_txt_problems(dist) == []
    write(dist, "robots.txt", "User-agent: *\nDisallow:\n")
    assert robots_txt_problems(dist) == ["robots.txt does not name the sitemap"]


def test_the_open_site_refuses_a_hidden_page(tmp_path, monkeypatch, hidden):
    dist = site(tmp_path)
    monkeypatch.setattr(check_dist, "expected_pages", lambda: ["/", "/about"])
    assert launched_problems(dist) == ["hidden page on the open site: /about (an operator placeholder has no value)"]
    monkeypatch.setattr(check_dist, "hidden_pages", lambda: set())
    assert launched_problems(dist) == []


def test_the_open_site_refuses_a_robots_txt_that_closes_the_whole_site(tmp_path, monkeypatch):
    dist = site(tmp_path)
    monkeypatch.setattr(check_dist, "hidden_pages", lambda: set())
    for closed in ("User-agent: *\nDisallow: /\nSitemap: https://arcanadiary.com/sitemap.xml\n",
                   "User-agent: *\ndisallow:/ \nSitemap: https://arcanadiary.com/sitemap.xml\n",
                   "User-agent: *\nDisallow: /*\nSitemap: https://arcanadiary.com/sitemap.xml\n"):
        write(dist, "robots.txt", closed)
        assert launched_problems(dist) == ["robots.txt closes the whole site (Disallow: /) on the open site"]
        assert robots_txt_problems(dist) == []  # the stage site may close itself
    write(dist, "robots.txt", "User-agent: *\nDisallow: /api/\nSitemap: https://arcanadiary.com/sitemap.xml\n")
    assert launched_problems(dist) == []


def test_main_launched_fails_on_hidden_pages(tmp_path, capsys, hidden):
    dist = site(tmp_path)
    assert check_dist.main(dist) == 0
    capsys.readouterr()
    assert check_dist.main(dist, launched=True) == 1
    assert capsys.readouterr().out.count("hidden page on the open site") == 8


def test_a_dynamic_import_of_the_library_is_fine(tmp_path):
    dist = site(tmp_path)
    names = {f.name for f in static_chunks(dist, ISLAND)}
    assert names == {"ReadingIsland.a1.js", "client.b2.js", "preact.c3.js", "api.d4.js"}
    assert auth_problems(dist) == []


def test_a_static_import_of_the_library_is_reported(tmp_path):
    dist = site(tmp_path, 'import{A as G}from"./supabaseClient.e5.js";')
    assert auth_problems(dist) == [f"{path} loads the sign-in library at start" for path in READING_PAGES]


def test_a_build_without_the_library_chunk_is_reported(tmp_path):
    dist = site(tmp_path, "")
    (dist / "_astro/supabaseClient.e5.js").unlink()
    assert auth_problems(dist) == ["no chunk of the sign-in library in site/dist/_astro (src/lib/supabaseClient.ts not built?)"]


def test_card_lists_have_all_their_distinct_card_links(tmp_path):
    dist = site(tmp_path)
    assert list_problems(dist) == []
    assert sum(c["yes_no"] == "yes" for c in DECK) == 45 and sum(c["yes_no"] == "no" for c in DECK) == 13


def test_a_shrunk_card_list_is_reported(tmp_path):
    dist = site(tmp_path)
    list_pages(dist, drop=-1)
    problems = list_problems(dist)
    assert "77 distinct card links instead of 78: site/dist/yes-no/cards.html" not in problems  # one per block: 75
    assert "44 card links in block lean-yes instead of 45: site/dist/yes-no/cards.html" in problems
    assert "12 card links in block lean-no instead of 13: site/dist/yes-no/cards.html" in problems
    write(dist, "cards.html", links(DECK[:-1], "en"))
    write(dist, "es/cartas/arcanos-mayores.html", "")
    problems = list_problems(dist)
    assert "77 distinct card links instead of 78: site/dist/cards.html" in problems
    assert "0 distinct card links instead of 22: site/dist/es/cartas/arcanos-mayores.html" in problems


def test_a_link_to_a_hidden_page_is_reported(tmp_path, hidden):
    dist = site(tmp_path)
    assert hidden_link_problems(dist) == []
    write(dist, "es.html", head("/es") + '<a href="/privacy">p</a><a href="https://arcanadiary.com/es/terminos#x">t</a>')
    assert hidden_link_problems(dist) == ["link to the hidden page /es/terminos: site/dist/es.html",
                                          "link to the hidden page /privacy: site/dist/es.html"]


def test_a_good_build_has_no_markup_problem(tmp_path):
    assert markup_problems(site(tmp_path)) == []


def test_two_links_to_one_address_in_main_are_reported_but_not_inside_nav(tmp_path):
    # SEO Monster 2027, 4.4: the first link in the DOM gives the anchor; navigation sits in <nav>
    dist = site(tmp_path)
    crumbs = '<nav><a href="/">Home</a><a href="/cards">Cards</a></nav>'
    write(dist, "cards/the-moon.html", head("/cards/the-moon") + f'<main id="main">{crumbs}<p><a href="/cards#cups">Cups</a> '
          '<a href="/cards/the-sun">The Sun</a> <a href="#love">Love</a> <a href="#love">Love</a></p>'
          '<aside><a href="https://arcanadiary.com/cards/the-sun#love">XIX The Sun</a></aside>'
          '<nav id="card-nav"><a href="/cards/the-sun">Next</a></nav></main>'
          '<footer><a href="/cards/the-sun">The Sun</a></footer><time datetime="2026-11-23">x</time>')
    write(dist, "index.html", head("/") + '<main><a href="/daily">Card of the Day</a><a href="/daily">Turn it over</a></main>')
    assert markup_problems(dist) == ["2 links to /cards/the-sun in <main> outside <nav>: site/dist/cards/the-moon.html",
                                     "2 links to /daily in <main> outside <nav>: site/dist/index.html"]


def test_related_cards_in_a_nav_inside_the_aside_repeat_a_card_of_the_text(tmp_path):
    # owner decision 40: the whole "Related cards" block is navigation (<nav> in the <aside>), the text keeps its link
    dist = site(tmp_path)
    write(dist, "cards/the-moon.html", head("/cards/the-moon") + '<main id="main"><p><a href="/cards/the-sun">The Sun</a></p>'
          '<aside id="related"><nav aria-labelledby="related-title"><h2 id="related-title">Related cards</h2><ul>'
          '<li><a href="/cards/the-sun">XIX The Sun</a></li><li><a href="/cards/the-star">XVII The Star</a></li></ul></nav>'
          '</aside></main><time datetime="2026-11-23">x</time>')
    assert markup_problems(dist) == []
    write(dist, "cards/the-moon.html", head("/cards/the-moon") + '<main id="main"><p><a href="/cards/the-sun">The Sun</a></p>'
          '<aside id="related"><h2>Related cards</h2><ul><li><a href="/cards/the-sun">XIX The Sun</a></li></ul></aside>'
          '</main><time datetime="2026-11-23">x</time>')
    assert markup_problems(dist) == ["2 links to /cards/the-sun in <main> outside <nav>: site/dist/cards/the-moon.html"]


def test_a_footer_link_to_the_page_itself_needs_aria_current(tmp_path):
    dist = site(tmp_path)
    write(dist, "yes-no.html", head("/yes-no") + '<main></main><footer><a href="/yes-no">Yes or No</a>'
          '<a href="/love">Love</a></footer>')
    write(dist, "es.html", head("/es") + '<main></main><footer><a href="/es#una-carta" aria-current="page">Una carta</a></footer>')
    write(dist, "love.html", head("/love") + '<main></main><footer><a href="/love" aria-current="true">Love</a></footer>')
    assert markup_problems(dist) == ["footer link to the page itself without aria-current=\"page\": /love: site/dist/love.html",
                                     "footer link to the page itself without aria-current=\"page\": /yes-no: site/dist/yes-no.html"]


def test_link_text_that_runs_together_is_reported(tmp_path):
    # the text of a link is what a crawler, a screen reader and a language model read: "PreviousXVII" is no word
    dist = site(tmp_path)
    good = ('<a href="/cards/the-star"><small>← Previous</small> XVII The Star</a>'
            '<a href="/one-card"><span>One card</span> <span>A single card</span></a>'
            '<a href="/cards/the-sun"><b>XIX</b> The Sun</a><a href="/x">Haz una <b>tirada</b>, ya</a>')
    write(dist, "love.html", head("/love") + f"<main>{good}</main>")
    assert markup_problems(dist) == []
    bad = ('<a href="/cards/the-star"><small>← Previous</small>XVII The Star</a>'
           '<a href="/one-card"><span>One card</span><span>A single card</span></a>')
    write(dist, "love.html", head("/love") + f"<main>{bad}</main>")
    assert markup_problems(dist) == ["link text runs together «← PreviousXVII The Star»: site/dist/love.html",
                                     "link text runs together «One cardA single card»: site/dist/love.html"]


def test_a_card_page_dates_its_review_with_time(tmp_path):
    dist = site(tmp_path)
    write(dist, "es/cartas/la-luna.html", head("/es/cartas/la-luna") + '<main><p>La revisó X el 23 de noviembre de 2026.</p></main>')
    assert markup_problems(dist) == ["no <time datetime> of the review date: site/dist/es/cartas/la-luna.html"]


def test_main_reports_every_problem_and_passes_a_good_build(tmp_path, capsys):
    assert check_dist.main(tmp_path / "nothing") == 1
    out = capsys.readouterr().out
    assert "missing: site/dist/diary.html" in out and "missing: site/dist/sitemap.xml" in out
    assert check_dist.main(site(tmp_path)) == 0
    assert capsys.readouterr().out == "OK: 187 pages\n"

def test_a_build_without_the_service_worker_fails(tmp_path, capsys):
    """Stage 8.1: /sw.js is a file of the build (src/pages/sw.js.ts); without it the morning reminder cannot work."""
    dist = site(tmp_path)
    (dist / "sw.js").unlink()
    assert check_dist.main(dist) == 1
    assert "missing: " in capsys.readouterr().out
