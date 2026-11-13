"""Дизайн-токены Arcana Diary: проверка контраста и выгрузка в CSS.

Источник истины — docs/design/tokens.json (спецификация этапа 3, раздел 2).
Запуск из корня репозитория:
  python3 tools/design/tokens.py          — проверить контраст и записать docs/design/tokens.css
  python3 tools/design/tokens.py --check  — проверить контраст и что tokens.css совпадает с tokens.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "docs/design/tokens.json"
CSS = ROOT / "docs/design/tokens.css"
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def load(path: Path = TOKENS) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve(tokens: dict, path: str):
    value = tokens
    for key in path.split("."):
        value = value[key]
    return value


def luminance(hex_color: str) -> float:
    if not HEX.match(hex_color):
        raise ValueError(f"не цвет вида #RRGGBB: {hex_color}")
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast(tokens: dict) -> list[str]:
    errors = []
    for fg_path, bg_path, minimum in tokens["contrastPairs"]:
        ratio = contrast(resolve(tokens, fg_path), resolve(tokens, bg_path))
        if ratio < minimum:
            errors.append(f"{fg_path} на {bg_path}: {ratio:.2f} < {minimum}")
    return errors


def _flatten(prefix: str, value) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        out = []
        for key, inner in value.items():
            out += _flatten(f"{prefix}-{_kebab(key)}", inner)
        return out
    return [(prefix, str(value))]


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z0-9])", "-", name).lower()


def to_css(tokens: dict) -> str:
    lines = ["/* Сгенерировано tools/design/tokens.py из docs/design/tokens.json — не править руками. */", ":root {"]
    for name, value in _flatten("--color", tokens["color"]):
        lines.append(f"  {name}: {value};")
    lines.append(f"  --font-display: {tokens['font']['display']};")
    lines.append(f"  --font-text: {tokens['font']['text']};")
    for key, px in tokens["fontSize"].items():
        lines.append(f"  --font-size-{_kebab(key)}: {px}px;")
    for i, px in enumerate(tokens["space"], start=1):
        lines.append(f"  --space-{i}: {px}px;")
    for key, px in tokens["radius"].items():
        lines.append(f"  --radius-{_kebab(key)}: {px}px;")
    lines.append(f"  --motion-night-open: {tokens['motion']['nightOpenMs']}ms;")
    lines.append(f"  --motion-card-flip: {tokens['motion']['cardFlipMs']}ms;")
    lines.append(f"  --motion-easing: {tokens['motion']['easing']};")
    lines.append(f"  --card-thumb-height: {tokens['card']['thumbHeight']}px;")
    lines.append(f"  --card-ratio: {tokens['card']['masterWidth']} / {tokens['card']['masterHeight']};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    tokens = load()
    errors = check_contrast(tokens)
    css = to_css(tokens)
    if "--check" in argv[1:]:
        if not CSS.exists() or CSS.read_text(encoding="utf-8") != css:
            errors.append("docs/design/tokens.css не совпадает с tokens.json — запустите без --check")
    else:
        CSS.write_text(css, encoding="utf-8")
    for e in errors:
        print(e)
    print("OK" if not errors else f"ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
