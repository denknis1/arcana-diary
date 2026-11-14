import hashlib
import shutil
import subprocess

import pytest

from process_cards import check_scan, contact_sheet, cover_filter, out_height, out_name, process

RATIO = (700, 1200)
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="нет ffmpeg")


def test_out_names():
    assert out_name("the-moon", 700) == "the-moon.webp"
    assert out_name("the-moon", 350) == "the-moon@350.webp"
    assert out_name("the-moon", 160) == "the-moon@160.webp"


def test_out_height_is_7_by_12_and_even():
    assert [out_height(w, RATIO) for w in (700, 350, 160)] == [1200, 600, 274]


def test_cover_filter_numbers():
    assert cover_filter(700, 1200) == "scale=700:1200:force_original_aspect_ratio=increase:flags=lanczos,crop=700:1200"


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
    written = process(src, out, sources, deck, RATIO)
    assert len(written) == 6
    for i in (0, 1):                                          # разные сканы — один размер
        assert webp_size(out / f"card-{i}.webp") == (700, 1200)
        assert webp_size(out / f"card-{i}@350.webp") == (350, 600)
        assert webp_size(out / f"card-{i}@160.webp") == (160, 274)
    sheet = tmp_path / "sheet.jpg"
    contact_sheet(out, deck, sheet)
    assert sheet.stat().st_size > 0
