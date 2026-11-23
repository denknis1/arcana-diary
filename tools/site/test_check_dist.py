"""tools/site/check_dist.py on small hand-made builds (spec 4.4b §5, §6, §11): the private pages are noindex and the
sign-in library is never loaded at start by a reading page."""
import check_dist
from check_dist import PRIVATE, READING_PAGES, auth_problems, dist_file, expected_pages, robots_problems, static_chunks

ISLAND = '<astro-island component-url="/_astro/ReadingIsland.a1.js" renderer-url="/_astro/client.b2.js"></astro-island>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def write(dist, name, text):
    file = dist / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def site(tmp_path, reading_island: str):
    dist = tmp_path / "dist"
    for path in expected_pages():
        write(dist, dist_file(path), (NOINDEX if path in PRIVATE else "") + ISLAND)
    write(dist, "_astro/client.b2.js", 'import{h}from"./preact.c3.js";')
    write(dist, "_astro/preact.c3.js", "export const h=1;")
    write(dist, "_astro/ReadingIsland.a1.js", reading_island)
    write(dist, "_astro/api.d4.js", 'const l=()=>import("./supabaseClient.e5.js");export{l};')
    write(dist, "_astro/supabaseClient.e5.js", 'class GoTrueClient{};export{GoTrueClient as A};')
    return dist


def test_the_private_pages_are_expected():
    assert {"/diary", "/es/diario", "/account", "/es/cuenta"} <= set(expected_pages())
    assert len(expected_pages()) == 177


def test_only_the_private_pages_say_noindex(tmp_path):
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
    assert robots_problems(dist) == []
    write(dist, "diary.html", ISLAND)
    write(dist, "yes-no.html", NOINDEX + ISLAND)
    assert robots_problems(dist) == ["no noindex meta: site/dist/diary.html", "unexpected noindex meta: site/dist/yes-no.html"]


def test_a_dynamic_import_of_the_library_is_fine(tmp_path):
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
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
    assert "missing: site/dist/diary.html" in capsys.readouterr().out
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
    for name in check_dist.DATA_FILES:
        write(dist, name, "[]")
    assert check_dist.main(dist) == 0
    assert capsys.readouterr().out == "OK: 177 pages\n"
