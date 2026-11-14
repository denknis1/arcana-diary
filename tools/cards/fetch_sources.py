"""Список сканов «Roses & Lilies» (1909) с Wikimedia Commons и их скачивание.

Запуск из корня репозитория:
  python3 tools/cards/fetch_sources.py --list               — таблица 78 файлов: имя, размер, байты (без скачивания)
  python3 tools/cards/fetch_sources.py --download WORKDIR   — скачать в WORKDIR (только после «да» владельца),
                                                              сверить sha1 Commons, записать content/cards/sources.json
"""
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS_CSV = ROOT / "docs/research/stage1/cards.csv"
SOURCES = ROOT / "content/cards/sources.json"
API = "https://commons.wikimedia.org/w/api.php"
CATEGORY = "Category:Rider-Waite tarot deck (Roses & Lilies)"
USER_AGENT = "tarot-scans-fetch/1.0 (one-time download of 78 public-domain scans)"
PAUSE_S = 3          # пауза между файлами
RETRY_WAIT_S = 30    # ожидание после 429/503, если сервер не прислал Retry-After
ATTEMPTS = 5
TITLE_RE = re.compile(r"^File:RWS1909 - (?:(\d{2}) [A-Za-z ]+|(Wands|Cups|Swords|Pentacles) (\d{2}))\.jpe?g$")


def card_id_for(title: str, rows: list[dict]) -> str | None:
    """«File:RWS1909 - 18 Moon.jpeg» → major-18-moon; «… - Cups 14.jpeg» → cups-14-king; иначе None."""
    m = TITLE_RE.match(title)
    if not m:
        return None
    if m.group(1) is not None:
        arcana, suit, rank = "major", "", int(m.group(1))
    else:
        arcana, suit, rank = "minor", m.group(2).lower(), int(m.group(3))
    for r in rows:
        if r["arcana"] == arcana and r["suit"] == suit and int(r["rank"]) == rank:
            return r["card_id"]
    return None


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_files() -> list[dict]:
    """Все файлы категории с url, размерами и sha1 (API Commons, без скачивания картинок)."""
    params = {"action": "query", "format": "json", "generator": "categorymembers", "gcmtitle": CATEGORY,
              "gcmtype": "file", "gcmlimit": "100", "prop": "imageinfo", "iiprop": "url|size|sha1"}
    files = []
    while True:
        data = _get(params)
        for page in data.get("query", {}).get("pages", {}).values():
            info = page["imageinfo"][0]
            files.append({"commons_title": page["title"], "url": info["url"], "width": info["width"],
                          "height": info["height"], "bytes": info["size"], "sha1": info["sha1"]})
        if "continue" not in data:
            return files
        params.update(data["continue"])


def match_cards(files: list[dict], rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Сопоставить файлы картам; вернуть 78 записей в порядке cards.csv и список ошибок."""
    by_card, errors = {}, []
    for f in files:
        cid = card_id_for(f["commons_title"], rows)
        if cid is None:
            continue
        if cid in by_card:
            errors.append(f"две картинки для {cid}: {by_card[cid]['commons_title']} и {f['commons_title']}")
        by_card[cid] = {"card_id": cid, **f}
    missing = [r["card_id"] for r in rows if r["card_id"] not in by_card]
    if missing:
        errors.append(f"нет файлов для: {', '.join(missing)}")
    return [by_card[r["card_id"]] for r in rows if r["card_id"] in by_card], errors


def _fetch(url: str) -> bytes:
    """Скачать файл; на 429/503 ждать, сколько просит сервер (Retry-After), и повторить — до ATTEMPTS раз."""
    for attempt in range(ATTEMPTS):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == ATTEMPTS - 1:
                raise
            retry = (e.headers.get("Retry-After") or "") if e.headers else ""
            time.sleep(int(retry) if retry.isdigit() else RETRY_WAIT_S * (attempt + 1))


def download(entries: list[dict], workdir: Path) -> list[dict]:
    workdir.mkdir(parents=True, exist_ok=True)
    sources = []
    for e in entries:
        path = workdir / e["commons_title"].removeprefix("File:")
        if not path.exists():
            path.write_bytes(_fetch(e["url"]))
            time.sleep(PAUSE_S)
        data = path.read_bytes()
        if hashlib.sha1(data).hexdigest() != e["sha1"] or len(data) != e["bytes"]:
            raise SystemExit(f"{path.name}: sha1 или размер не совпадают с Commons — файл удалить и скачать заново")
        sources.append({"card_id": e["card_id"], "commons_title": e["commons_title"], "url": e["url"],
                        "sha256": hashlib.sha256(data).hexdigest(), "width": e["width"], "height": e["height"],
                        "bytes": e["bytes"]})
    return sources


def main(argv: list[str]) -> int:
    with open(CARDS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    entries, errors = match_cards(list_files(), rows)
    if errors:
        print("\n".join(errors))
        return 1
    if "--list" in argv:
        for e in entries:
            print(f"{e['card_id']}\t{e['commons_title']}\t{e['width']}×{e['height']}\t{e['bytes']}")
        print(f"всего {len(entries)} файлов, {sum(e['bytes'] for e in entries) / 1e6:.1f} МБ")
        return 0
    if "--download" in argv:
        workdir = Path(argv[argv.index("--download") + 1])
        sources = download(entries, workdir)
        SOURCES.parent.mkdir(parents=True, exist_ok=True)
        SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {len(sources)} файлов в {workdir}, записан {SOURCES.relative_to(ROOT)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
