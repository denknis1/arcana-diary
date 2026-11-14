import hashlib
import shutil
import subprocess

import pytest

from process_cards import art_height, check_scan, contact_sheet, crop_filter, crop_for, out_name, process

CROP = {"top": 0.1, "bottom": 0.1, "sides": 0.05}
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="нет ffmpeg")


def test_out_names():
    assert out_name("the-moon", 700) == "the-moon.webp"
    assert out_name("the-moon", 350) == "the-moon@350.webp"
    assert out_name("the-moon", 160) == "the-moon@160.webp"


def test_crop_filter_numbers():
    assert crop_filter(1000, 2000, CROP, 700, 1400) == (
        "crop=900:1600:50:200,scale=700:1400:force_original_aspect_ratio=increase:flags=lanczos,crop=700:1400")


def test_crop_filter_asymmetric_left_right():
    crop = {"top": 0.1, "bottom": 0.1, "left": 0.02, "right": 0.08}
    assert crop_filter(1000, 2000, crop, 700, 1400) == (
        "crop=900:1600:20:200,scale=700:1400:force_original_aspect_ratio=increase:flags=lanczos,crop=700:1400")


def test_crop_for_merges_overrides():
    assert crop_for("a", CROP, None) == {"top": 0.1, "bottom": 0.1, "left": 0.05, "right": 0.05}
    assert crop_for("a", CROP, {"b": {"top": 0.2}}) == {"top": 0.1, "bottom": 0.1, "left": 0.05, "right": 0.05}
    assert crop_for("a", CROP, {"a": {"top": 0.12, "right": 0.09}}) == {
        "top": 0.12, "bottom": 0.1, "left": 0.05, "right": 0.09}


def test_art_height_median_even():
    sources = [{"width": 1000, "height": 2000}, {"width": 1000, "height": 2100}, {"width": 1000, "height": 1900}]
    # медиана: 2000 × 0.8 / 900 = 1.777… → 700 × 1.777 = 1244.4 → 1244
    assert art_height(sources, CROP, 700) == 1244
    assert art_height(sources, CROP, 160) % 2 == 0


def test_check_scan_rejects_wrong_hash(tmp_path):
    scan = tmp_path / "a.jpeg"
    scan.write_bytes(b"not the scan")
    with pytest.raises(SystemExit):
        check_scan(scan, {"sha256": "0" * 64})


def make_scan(path, w, h):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c=white:s={w}x{h},drawbox=x=40:y=140:w={w - 80}:h={h - 280}:color=navy:t=fill",
                    "-frames:v", "1", str(path)], check=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def webp_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return tuple(int(v) for v in out.stdout.strip().split(","))


@needs_ffmpeg
def test_process_writes_three_sizes_and_sheet(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    sources, deck = [], []
    for i, (w, h) in enumerate([(820, 1430), (850, 1450)]):
        title = f"File:RWS1909 - 0{i} Test.jpeg"
        sha = make_scan(src / title.removeprefix("File:"), w, h)
        sources.append({"card_id": f"c{i}", "commons_title": title, "sha256": sha, "width": w, "height": h})
        deck.append({"card_id": f"c{i}", "image": f"card-{i}", "order": i + 1})
    out = tmp_path / "out"
    written = process(src, out, sources, deck, CROP)
    assert len(written) == 6
    h700 = art_height(sources, CROP, 700)
    assert webp_size(out / "card-0.webp") == (700, h700)
    assert webp_size(out / "card-1.webp") == (700, h700)      # разные сканы — один размер
    assert webp_size(out / "card-1@160.webp") == (160, art_height(sources, CROP, 160))
    sheet = tmp_path / "sheet.jpg"
    contact_sheet(out, deck, sheet)
    assert sheet.stat().st_size > 0
