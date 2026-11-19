import pytest

from app.reader.sections import Event, SectionParser, required_sections

ANSWER = ("[[headline]]\nA calm way forward.\n[[card 1]]\nThe Fool can suggest a fresh start.\n"
          "[[step]]\nWrite one line today.\n")


def feed_all(chunks):
    parser = SectionParser()
    events = []
    for chunk in chunks:
        events += parser.feed(chunk)
    events += parser.finish()
    return parser, events


def texts(events, names):
    return {n: "".join(e.text for e in events if e.kind == "text" and e.name == n) for n in names}


def test_whole_answer_in_one_chunk():
    parser, events = feed_all([ANSWER])
    assert parser.sections() == {"headline": "A calm way forward.", "card1": "The Fool can suggest a fresh start.",
                                 "step": "Write one line today."}
    assert [e.name for e in events if e.kind == "section"] == ["headline", "card1", "step"]


def test_char_by_char_gives_same_result():
    whole, e1 = feed_all([ANSWER])
    chars, e2 = feed_all(list(ANSWER))
    assert chars.sections() == whole.sections()
    assert texts(e2, whole.sections()) == texts(e1, whole.sections())


def test_marker_split_across_chunks():
    parser, _ = feed_all(["[[hea", "dline]]\nHi there.\n[[ste", "p]]\nGo."])
    assert parser.sections() == {"headline": "Hi there.", "step": "Go."}


def test_marker_inside_a_line_is_text():
    parser, _ = feed_all(["[[headline]]\nSee [[step]] here.\n"])
    assert parser.sections() == {"headline": "See [[step]] here."}


def test_text_after_a_partial_line_is_not_a_marker():
    parser, _ = feed_all(["[[headline]]\nabc", "[[step]]\n"])
    assert parser.sections() == {"headline": "abc[[step]]"}


def test_text_before_first_marker_goes_to_headline():
    parser, events = feed_all(["Hello.\n[[card 1]]\nOne.\n"])
    assert parser.sections() == {"headline": "Hello.", "card1": "One."}
    assert events[0] == Event("section", "headline")


def test_unknown_marker_stays_text():
    parser, _ = feed_all(["[[headline]]\nHi.\n[[notes]]\nMore.\n"])
    assert parser.sections() == {"headline": "Hi.\n[[notes]]\nMore."}


def test_finish_flushes_last_marker_and_text():
    _, events = feed_all(["[[headline]]\nHi.\n[[why]]"])
    assert events[-1] == Event("section", "why")
    parser, _ = feed_all(["[[headline]]\nNo newline at the end"])
    assert parser.sections() == {"headline": "No newline at the end"}


def test_brackets_in_text_pass_through():
    parser, _ = feed_all(["[[headline]]\n", "[note] stays.\n"])
    assert parser.sections() == {"headline": "[note] stays."}


def test_marker_spelling_variants():
    parser, _ = feed_all(["[[ Headline ]]\nA.\n[[Card 2]]\nB.\n[[card3]]\nC.\n"])
    assert parser.sections() == {"headline": "A.", "card2": "B.", "card3": "C."}


def test_text_on_the_marker_line():
    answer = "[[headline]] A calm way.\n[[card 1]] One card.\nMore.\n[[step]]Go.\n"
    whole, _ = feed_all([answer])
    chars, _ = feed_all(list(answer))
    assert whole.sections() == chars.sections() == {"headline": "A calm way.", "card1": "One card.\nMore.",
                                                    "step": "Go."}


def test_markdown_around_markers():
    parser, _ = feed_all(["**[[headline]]**\nA.\n## [[Step]]\nGo.\n__[[why]]__ W.\n"])
    assert parser.sections() == {"headline": "A.", "step": "Go.", "why": "W."}


def test_bold_text_is_not_held_back():
    _, events = feed_all(["[[headline]]\n", "**Calm** start"])
    assert texts(events, ["headline"]) == {"headline": "**Calm** start"}


def test_crisis_marker_and_order_seen():
    parser, events = feed_all(["[[crisis]]\n"])
    assert parser.seen == ["crisis"] and events == [Event("section", "crisis")]
    parser, _ = feed_all(["Hi.\n[[card 1]]\nA.\n[[step]]\nB."])
    assert parser.seen == ["headline", "card1", "step"]


@pytest.mark.parametrize("kind, with_why, expected", [
    ("one", False, ["headline", "card1", "step"]),
    ("card_page", False, ["headline", "card1", "step"]),
    ("yes_no", True, ["headline", "card1", "step", "why"]),
    ("yes_no", False, ["headline", "card1", "step"]),
    ("three", False, ["headline", "card1", "card2", "card3", "synthesis", "step"]),
])
def test_required_sections(kind, with_why, expected):
    assert required_sections(kind, with_why) == expected


def test_crisis_marker_inline_is_crisis_and_never_shown():
    parser, events = feed_all(["[[headline]]\nI'm worried about you. [[crisis]] Please reach out.\n"])
    assert "crisis" in parser.seen
    assert "[[" not in "".join(e.text for e in events if e.kind == "text")


@pytest.mark.parametrize("chunks", [
    ["[[headline]]\nI'm worried. [[cri", "sis]] Please reach out.\n"],
    ["[[headline]]\nI'm worried. [", "[ Crisis ]", "] Please.\n"],
    list("[[headline]]\nI'm worried. [[crisis]] Please.\n"),
    ["I'm worried. [[CRISIS]]"],
])
def test_crisis_marker_inline_split_across_chunks(chunks):
    parser, events = feed_all(chunks)
    assert "crisis" in parser.seen
    visible = "".join(e.text for e in events if e.kind == "text")
    assert "[[cri" not in visible and "sis]]" not in visible


def test_other_marker_partial_inline_is_text():
    parser, _ = feed_all(["[[headline]]\nSee [[ste", "p]] here.\n"])
    assert parser.sections() == {"headline": "See [[step]] here."}


def test_trailing_bracket_is_flushed_at_the_end():
    parser, _ = feed_all(["[[headline]]\nAn aside [[cri"])
    assert parser.sections() == {"headline": "An aside [[cri"}


def test_crlf_split_across_chunks_does_not_leak_the_marker():
    parser, events = feed_all(["[[headline]]\r\nHi.\r\n[[card 1]]\r", "\nOne.\r\n"])
    assert parser.sections() == {"headline": "Hi.", "card1": "One."}
    assert "[[card 1]]" not in "".join(e.text for e in events if e.kind == "text")


def test_bracket_at_line_end_keeps_its_newline():
    parser, events = feed_all(["[[headline]]\nSee [\nNext line"])
    assert parser.sections() == {"headline": "See [\nNext line"}


def test_bracket_at_line_end_before_a_marker():
    parser, _ = feed_all(["[[headline]]\nSee [\n[[step]]\nGo"])
    assert parser.sections()["step"] == "Go"


def test_bracket_then_crisis_on_the_next_line_is_not_crisis():
    parser, _ = feed_all(["[[headline]]\nSee [", "\n[crisis]]\n"])
    assert "crisis" not in parser.seen
