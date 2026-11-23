"""tools/site/check_dist.py on small hand-made builds (spec 4.4b §5, §6, §11; stage 6 §8): every page exists, an
indexable page has its head and JSON-LD, no placeholder is left, private and hidden pages are noindex and out of the
sitemap and of every hreflang pair, and the sign-in library is never loaded at start by a reading page."""
import check_dist
from check_dist import (EXTRA, READING_PAGES, auth_problems, canonical, dist_file, expected_alternates, expected_pages,
                        head_problems, hidden_pages, indexable_pages, launched_problems, noindex_pages,
                        hreflang_target_problems, placeholder_problems, robots_problems, robots_txt_problems,
                        sitemap_problems, static_chunks)

ISLAND = '<astro-island component-url="/_astro/ReadingIsland.a1.js" renderer-url="/_astro/client.b2.js"></astro-island>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
LD = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>'
ROBOTS_TXT = "User-agent: *\nDisallow:\nSitemap: https://arcanadiary.com/sitemap.xml\n"


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
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset>'
            + "".join(f"<url><loc>{canonical(p)}</loc></url>" for p in paths) + "</urlset>")


def site(tmp_path, reading_island='import{x}from"./api.d4.js";'):
    dist = tmp_path / "dist"
    for path in expected_pages():
        write(dist, dist_file(path), head(path) + ISLAND)
    write(dist, "_astro/client.b2.js", 'import{h}from"./preact.c3.js";')
    write(dist, "_astro/preact.c3.js", "export const h=1;")
    write(dist, "_astro/ReadingIsland.a1.js", reading_island)
    write(dist, "_astro/api.d4.js", 'const l=()=>import("./supabaseClient.e5.js");export{l};')
    write(dist, "_astro/supabaseClient.e5.js", 'class GoTrueClient{};export{GoTrueClient as A};')
    write(dist, "data/daily-en.json", "[]")
    write(dist, "data/daily-es.json", "[]")
    write(dist, "sitemap.xml", sitemap(indexable_pages()))
    write(dist, "robots.txt", ROBOTS_TXT)
    return dist


def test_every_page_of_stage_6_part_1_is_expected():
    pages = expected_pages()
    assert len(pages) == 177
    assert {"/diary", "/es/diario", "/account", "/es/cuenta", "/cards", "/yes-no/cards", "/es/tiradas/3-cartas"} <= set(pages)


def test_hreflang_follows_mutual_pairs_only():
    assert expected_alternates("/yes-no") == {("en", "https://arcanadiary.com/yes-no"),
                                              ("es", "https://arcanadiary.com/es/si-o-no"),
                                              ("x-default", "https://arcanadiary.com/yes-no")}
    # no mutual pair, no hreflang at all (stage 2 spec §3)
    assert expected_alternates("/one-card") == set()
    assert expected_alternates("/es/tiradas/3-cartas") == set()
    assert canonical("/") == "https://arcanadiary.com/"


def test_a_pair_with_a_hidden_page_is_no_hreflang_pair(monkeypatch):
    monkeypatch.setattr(check_dist, "pairs", lambda: {"/yes-no": "/es/sobre-nosotros", "/es/sobre-nosotros": "/yes-no"})
    assert expected_alternates("/yes-no") == set()


def test_hidden_pages_are_the_service_pages_with_an_operator_placeholder():
    assert hidden_pages() == {"/about", "/contact", "/privacy", "/terms", "/es/sobre-nosotros", "/es/contacto",
                              "/es/privacidad", "/es/terminos"}


def test_only_the_private_and_hidden_pages_say_noindex(tmp_path):
    dist = site(tmp_path)
    assert robots_problems(dist) == []
    write(dist, "diary.html", ISLAND)
    write(dist, "yes-no.html", NOINDEX + ISLAND)
    assert robots_problems(dist) == ["no noindex meta: site/dist/diary.html", "unexpected noindex meta: site/dist/yes-no.html"]


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
        "canonical https://arcanadiary.com/cards/ instead of https://arcanadiary.com/cards: site/dist/cards.html",
        "JSON-LD does not parse: site/dist/cards.html",
        "no title: site/dist/love.html",
        "no description: site/dist/love.html",
        "canonical None instead of https://arcanadiary.com/love: site/dist/love.html",
        "hreflang [] instead of [('en', 'https://arcanadiary.com/love'), ('es', 'https://arcanadiary.com/es/amor'), "
        "('x-default', 'https://arcanadiary.com/love')]: site/dist/love.html",
        "no JSON-LD: site/dist/love.html",
    ]


def test_an_hreflang_link_to_a_noindex_or_hidden_page_is_reported(tmp_path):
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


def test_the_sitemap_lists_exactly_the_indexable_pages(tmp_path):
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


def test_the_open_site_refuses_a_hidden_page(monkeypatch):
    monkeypatch.setattr(check_dist, "expected_pages", lambda: ["/", "/about"])
    assert launched_problems() == ["hidden page on the open site: /about (an operator placeholder has no value)"]


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


def test_main_reports_every_problem_and_passes_a_good_build(tmp_path, capsys):
    assert check_dist.main(tmp_path / "nothing") == 1
    out = capsys.readouterr().out
    assert "missing: site/dist/diary.html" in out and "missing: site/dist/sitemap.xml" in out
    assert check_dist.main(site(tmp_path)) == 0
    assert capsys.readouterr().out == "OK: 177 pages\n"
