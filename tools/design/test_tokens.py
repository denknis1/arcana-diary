import pytest

from tokens import check_contrast, contrast, load, resolve, to_css


def test_contrast_black_white_is_21():
    assert round(contrast("#000000", "#FFFFFF"), 2) == 21.0


def test_contrast_same_color_is_1():
    assert contrast("#8E4A62", "#8E4A62") == pytest.approx(1.0)


def test_contrast_rejects_non_hex():
    with pytest.raises(ValueError):
        contrast("rgba(0,0,0,0.5)", "#FFFFFF")


def test_resolve_dotted_path():
    assert resolve({"color": {"day": {"bg": "#F7F2EC"}}}, "color.day.bg") == "#F7F2EC"


def test_check_contrast_reports_failing_pair():
    tokens = {"color": {"a": "#777777", "b": "#888888"}, "contrastPairs": [["color.a", "color.b", 4.5]]}
    errors = check_contrast(tokens)
    assert len(errors) == 1 and "color.a на color.b" in errors[0]


def test_to_css_has_variables_with_units():
    css = to_css(load())
    assert "--color-day-bg: #F7F2EC;" in css
    assert "--color-suit-night-majors: #C9A45C;" in css
    assert "--font-size-body: 16px;" in css
    assert "--space-1: 4px;" in css
    assert "--radius-panel-large: 28px;" in css
    assert "--motion-card-flip: 800ms;" in css


def test_project_tokens_pass_contrast():
    assert check_contrast(load()) == []


def test_body_text_not_below_16px():
    assert load()["fontSize"]["body"] >= 16
