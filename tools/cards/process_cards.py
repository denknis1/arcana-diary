"""Рисунки колоды: сканы «Roses & Lilies» → WebP 700/350/160 px в site/public/cards/ и контактный лист.

Запуск из корня репозитория:
  python3 tools/cards/process_cards.py SRC_DIR                                — все 78 карт в site/public/cards/
  python3 tools/cards/process_cards.py SRC_DIR --only ID,ID --out WORKDIR     — проба обрезки на нескольких картах
  python3 tools/cards/process_cards.py SRC_DIR --sheet WORKDIR/contact-sheet.jpg  — плюс контактный лист
SRC_DIR — папка со сканами из fetch_sources.py; доли обрезки — card.artCrop в docs/design/tokens.json.
"""
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content/cards"
TOKENS = ROOT / "docs/design/tokens.json"
OUT = ROOT / "site/public/cards"
WIDTHS = (700, 350, 160)
QUALITY = 75
SHEET_COLUMNS = 13


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def out_name(slug: str, width: int) -> str:
    return f"{slug}.webp" if width == WIDTHS[0] else f"{slug}@{width}.webp"


def art_height(sources: list[dict], crop: dict, width: int) -> int:
    """Высота выхода при ширине width: медианная пропорция обрезанных сканов, округлено до чётного."""
    ratios = [s["height"] * (1 - crop["top"] - crop["bottom"]) / (s["width"] * (1 - 2 * crop["sides"]))
              for s in sources]
    return 2 * round(width * statistics.median(ratios) / 2)


def crop_filter(width: int, height: int, crop: dict, out_w: int, out_h: int) -> str:
    """Фильтр ffmpeg: срезать поля по долям, вписать с заполнением в out_w × out_h, лишнее срезать по центру."""
    x, y = round(width * crop["sides"]), round(height * crop["top"])
    cw = width - 2 * x
    ch = height - y - round(height * crop["bottom"])
    return (f"crop={cw}:{ch}:{x}:{y},scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h}")


def check_scan(path: Path, source: dict) -> None:
    if not path.exists():
        raise SystemExit(f"нет скана {path}")
    data = path.read_bytes()
    if "bytes" in source and len(data) != source["bytes"]:
        raise SystemExit(f"{path.name}: размер {len(data)} байт не совпадает с sources.json ({source['bytes']})")
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise SystemExit(f"{path.name}: sha256 не совпадает с sources.json")


def run_ffmpeg(src: Path, vf: str, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf,
                    "-c:v", "libwebp", "-quality", str(QUALITY), "-compression_level", "6", str(dst)], check=True)


def process(src_dir: Path, out_dir: Path, sources: list[dict], deck: list[dict], crop: dict,
            only: set[str] | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {c["card_id"]: c for c in deck}
    heights = {w: art_height(sources, crop, w) for w in WIDTHS}
    written = []
    for s in sources:
        if only and s["card_id"] not in only:
            continue
        src = src_dir / s["commons_title"].removeprefix("File:")
        check_scan(src, s)
        for w in WIDTHS:
            dst = out_dir / out_name(by_id[s["card_id"]]["image"], w)
            run_ffmpeg(src, crop_filter(s["width"], s["height"], crop, w, heights[w]), dst)
            written.append(dst)
    return written


def contact_sheet(out_dir: Path, deck: list[dict], dst: Path, only: set[str] | None = None) -> None:
    """Все миниатюры 160 px сеткой по 13 в ряд, в порядке колоды, с серым зазором — видно края и обрезку."""
    cards = [c for c in sorted(deck, key=lambda c: c["order"]) if not only or c["card_id"] in only]
    rows = -(-len(cards) // SHEET_COLUMNS)
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate(cards):
            shutil.copy(out_dir / out_name(c["image"], 160), Path(tmp) / f"{i:03d}.webp")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{tmp}/%03d.webp",
                        "-vf", f"pad=iw+8:ih+8:4:4:color=gray,tile={SHEET_COLUMNS}x{rows}",
                        "-frames:v", "1", "-q:v", "3", str(dst)], check=True)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 2
    src_dir = Path(args[0])
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else OUT
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    sources = load_json(CONTENT / "sources.json")
    deck = load_json(CONTENT / "deck.json")
    crop = load_json(TOKENS)["card"]["artCrop"]
    written = process(src_dir, out_dir, sources, deck, crop, only)
    print(f"OK: {len(written)} файлов в {out_dir}")
    if "--sheet" in args:
        sheet = Path(args[args.index("--sheet") + 1])
        contact_sheet(out_dir, deck, sheet, only)
        print(f"контактный лист: {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
