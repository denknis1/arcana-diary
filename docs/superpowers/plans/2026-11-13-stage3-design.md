# Этап 3: дизайн и пользовательский путь — план работ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Утверждённые владельцем дизайн-система Arcana Diary, прототипы ключевых экранов EN/ES с кликабельными путями П1–П3, проверка Fable 5.2 и план событий аналитики — по ним этап 4 строит продукт.

**Architecture:** Визуальная работа идёт в Claude Design: дизайн-система — артефакт типа «Design System», прототипы — холст типа «Design». Значения дизайн-системы живут в `docs/design/tokens.json` (источник истины для кода) и проверяются скриптом на контраст; `tokens.css` генерируется. Владелец утверждает дизайн-систему, первые экраны и итог; между точками утверждения работа идёт без остановок.

**Tech Stack:** Claude Design (Artifact-инструмент: типы Design System и Design), Python 3.12 стандартная библиотека + pytest (`~/arcana-diary/api/.venv/bin/pytest`), Google Fonts (Cormorant Garamond, Manrope).

Спецификация: `docs/superpowers/specs/2026-11-13-stage3-design-design.md`. Холст выбора направления: https://claude.ai/artifact/N6mvXdh4K5csjtULB3a98q.

**Исполнение:** этот план выполняется в основной сессии (superpowers:executing-plans): задачи 3–7 требуют Artifact-инструмента и утверждений владельца по ходу. Задача 2 (код) и задача 9 (проверка) — субагентами.

## Global Constraints

- Направление «Сумерки»: день — `#F7F2EC` фон, `#FFFFFF` поверхность, `#241E36` текст, `#5B5470` второстепенный, `#8E4A62` акцент, `#E6DDD2` линия; ночь — `#10163A` фон, `#161E48` поверхность, `#F1ECE2` текст, `#B9B4CC` второстепенный, `#C9A45C` золото.
- Шрифты: Cormorant Garamond 500/600 — заголовки и названия карт; Manrope 400–700 — текст и интерфейс; текст не меньше 16 px; шкала 56 / 44 / 32 / 24 / 20 / 16 / 14 / 12.
- Отступы — шаг 4 px; скругления: поле 12, панель 18 и 28, карта 10, кнопка — полностью круглая; карта — 700 × 1200, миниатюра 120 px высотой.
- Движение: раскрытие ночи ≈ 600 мс, переворот карты ≤ 800 мс; при «уменьшить движение» — появление без анимации.
- Доступность: контраст текста ≥ 4,5 : 1, касание ≥ 44 px, видимая рамка фокуса, настоящие `<button>`, `<a href>`, `<input>` с `<label>`.
- Запреты в путях: не спрашивать пол и ничего не требовать до ответа; вопрос необязателен; никаких окон, которые человек не вызвал; ничего не продавать внутри ответа; аналитика без cookie.
- Тексты в макетах — осмысленные, по запретам З1–З6 этапа 1 (без обещаний точности, предсказаний событий, запугивания, чтения третьих лиц); без «рыбы».
- Меню — 5 пунктов этапа 2: EN Reading · Yes or No · Love · Card of the Day · Card Meanings; ES Tirada · Sí o no · Amor · Carta del día · Significados; переключатель EN | ES.
- Скачивание файлов — только после того, как владелец видит точное имя, источник и размер и отвечает «да». Скачанное — в папку черновика, не в репозиторий.
- Коммиты — в ветку `stage3-design`, без `git push`; сообщение заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Холсты и дизайн-система приватны; в репозиторий идут ссылки и выгрузки.

## Карта файлов

| Файл | Задача |
|---|---|
| `docs/design/tokens.json`, `docs/design/tokens.css` | 2 |
| `tools/design/tokens.py`, `tools/design/test_tokens.py` | 2 |
| артефакт «Arcana Diary — дизайн-система» (Design System) | 3 |
| артефакт «Arcana Diary — прототипы» (Design) | 4–7 |
| `docs/design/00-design.md`, `docs/design/analytics-events.md` | 8 |
| `docs/design/review-fable.md` | 9 |
| `docs/design/99-changelog.md`, `docs/stages.md` | 10 |

---

### Task 1: Три скана карт для образцов

**Files:** только папка черновика `<scratchpad>/cards-src/` (не репозиторий).

Источник — Wikimedia Commons, серия «RWS Tarot» (Pamela Colman Smith, общественное достояние; сканы с пометкой источника muzendo.jp). Сведения сняты через API Commons 13.11.2026:

| Файл | Размер | Байт | Прямой адрес |
|---|---|---|---|
| `RWS_Tarot_18_Moon.jpg` | 1111 × 1919 | 859 000 | https://upload.wikimedia.org/wikipedia/commons/7/7f/RWS_Tarot_18_Moon.jpg |
| `RWS_Tarot_19_Sun.jpg` | 1114 × 1919 | 935 619 | https://upload.wikimedia.org/wikipedia/commons/1/17/RWS_Tarot_19_Sun.jpg |
| `RWS_Tarot_16_Tower.jpg` | 1109 × 1920 | 758 728 | https://upload.wikimedia.org/wikipedia/commons/5/53/RWS_Tarot_16_Tower.jpg |

Оговорка для этапа 4: план продукта советует для итоговой колоды сканы Йельской библиотеки Байнеке или издания «Roses & Lilies» и запрещает перерисованные версии U.S. Games (1971+). Серия «RWS Tarot» берётся только для образцов вида; выбор издания для 78 карт — этап 4.

- [ ] **Step 1: Получить «да» владельца** на скачивание трёх файлов из таблицы (имя, источник, размер — как выше).
- [ ] **Step 2: Скачать в отдельную пустую папку**

```bash
D=/tmp/claude-1000/-home-deploy/3f345a0f-65b6-4a66-9e08-52fbaf3c682b/scratchpad/cards-src && mkdir -p "$D" && cd "$D" && \
for f in 7/7f/RWS_Tarot_18_Moon.jpg 1/17/RWS_Tarot_19_Sun.jpg 5/53/RWS_Tarot_16_Tower.jpg; do \
  curl -sSfL -A "arcana-diary-design/1.0" -o "$(basename $f)" "https://upload.wikimedia.org/wikipedia/commons/$f"; done; \
ls -l; file *.jpg
```

Expected: три файла, размеры в байтах как в таблице, `file` — «JPEG image data … 1111x1919» и т. п. Иначе — удалить и сообщить владельцу.

---

### Task 2: Токены дизайн-системы и проверка контраста

**Files:**
- Create: `docs/design/tokens.json`
- Create: `tools/design/tokens.py`
- Create: `tools/design/test_tokens.py`
- Create (генерируется): `docs/design/tokens.css`

**Interfaces:**
- Produces: `docs/design/tokens.json` (ключи `color.day.*`, `color.night.*`, `color.suit.{day,night}.{wands,cups,swords,pentacles,majors}`, `font`, `fontSize`, `space`, `radius`, `motion`, `card`, `contrastPairs`); `tools/design/tokens.py`: `load(path) -> dict`, `resolve(tokens, "a.b.c")`, `luminance(hex) -> float`, `contrast(fg, bg) -> float`, `check_contrast(tokens) -> list[str]`, `to_css(tokens) -> str`, `main(argv) -> int`; CSS-переменные `--color-day-bg`, `--color-night-accent`, `--font-display`, `--font-text`, `--font-size-body`, `--space-1…8`, `--radius-*`, `--motion-*`, `--card-thumb-height`, `--card-ratio`. Задача 3 переносит эти значения в дизайн-систему; этапы 4 и 6 подключают `tokens.css`.

- [ ] **Step 1: Записать `docs/design/tokens.json`**

```json
{
  "version": "1.0",
  "color": {
    "day": {
      "bg": "#F7F2EC",
      "surface": "#FFFFFF",
      "text": "#241E36",
      "textMuted": "#5B5470",
      "accent": "#8E4A62",
      "line": "#E6DDD2"
    },
    "night": {
      "bg": "#10163A",
      "surface": "#161E48",
      "text": "#F1ECE2",
      "textMuted": "#B9B4CC",
      "accent": "#C9A45C",
      "line": "#5A5233"
    },
    "suit": {
      "day": {
        "wands": "#9A5B12",
        "cups": "#1E6E6A",
        "swords": "#3B5D85",
        "pentacles": "#4D6A2C",
        "majors": "#7E6022"
      },
      "night": {
        "wands": "#E0A85A",
        "cups": "#6FC2BB",
        "swords": "#9DB8DA",
        "pentacles": "#A9C27E",
        "majors": "#C9A45C"
      }
    }
  },
  "font": {
    "display": "'Cormorant Garamond', Georgia, serif",
    "text": "Manrope, system-ui, sans-serif"
  },
  "fontSize": {
    "display1": 56,
    "display2": 44,
    "h1": 32,
    "h2": 24,
    "h3": 20,
    "body": 16,
    "small": 14,
    "caption": 12
  },
  "space": [4, 8, 12, 16, 24, 32, 48, 64],
  "radius": {
    "card": 10,
    "field": 12,
    "panel": 18,
    "panelLarge": 28,
    "pill": 999
  },
  "motion": {
    "nightOpenMs": 600,
    "cardFlipMs": 800,
    "easing": "cubic-bezier(0.2, 0.7, 0.2, 1)"
  },
  "card": {
    "masterWidth": 700,
    "masterHeight": 1200,
    "thumbHeight": 120
  },
  "contrastPairs": [
    ["color.day.text", "color.day.bg", 4.5],
    ["color.day.textMuted", "color.day.bg", 4.5],
    ["color.day.textMuted", "color.day.surface", 4.5],
    ["color.day.accent", "color.day.bg", 4.5],
    ["color.day.accent", "color.day.surface", 4.5],
    ["color.day.surface", "color.day.text", 4.5],
    ["color.night.text", "color.night.bg", 4.5],
    ["color.night.textMuted", "color.night.bg", 4.5],
    ["color.night.textMuted", "color.night.surface", 4.5],
    ["color.night.accent", "color.night.bg", 4.5],
    ["color.night.bg", "color.night.accent", 4.5],
    ["color.suit.day.wands", "color.day.bg", 4.5],
    ["color.suit.day.cups", "color.day.bg", 4.5],
    ["color.suit.day.swords", "color.day.bg", 4.5],
    ["color.suit.day.pentacles", "color.day.bg", 4.5],
    ["color.suit.day.majors", "color.day.bg", 4.5],
    ["color.suit.night.wands", "color.night.bg", 4.5],
    ["color.suit.night.cups", "color.night.bg", 4.5],
    ["color.suit.night.swords", "color.night.bg", 4.5],
    ["color.suit.night.pentacles", "color.night.bg", 4.5],
    ["color.suit.night.majors", "color.night.bg", 4.5]
  ]
}
```

- [ ] **Step 2: Написать тесты `tools/design/test_tokens.py`**

```python
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
```

- [ ] **Step 3: Запустить — должны упасть**

Run: `cd ~/arcana-diary/tools/design && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `ModuleNotFoundError: No module named 'tokens'`.

- [ ] **Step 4: Написать `tools/design/tokens.py`**

```python
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
```

- [ ] **Step 5: Тесты и генерация CSS**

Run: `cd ~/arcana-diary/tools/design && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `8 passed`.

Run: `cd ~/arcana-diary && python3 tools/design/tokens.py && python3 tools/design/tokens.py --check && head -4 docs/design/tokens.css`
Expected: `OK`, `OK`, затем строка-комментарий, `:root {`, `--color-day-bg: #F7F2EC;`, `--color-day-surface: #FFFFFF;`.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary && git add docs/design/tokens.json docs/design/tokens.css tools/design/tokens.py tools/design/test_tokens.py && git commit -m "design(stage3): design tokens with contrast check and CSS export

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Артефакт «Arcana Diary — дизайн-система» и вид карты

**Files:** новый артефакт Claude Design (тип «Design System»); в репозитории — ничего (ссылку записывает задача 8).

**Interfaces:**
- Consumes: значения `docs/design/tokens.json` (задача 2), три скана (задача 1).
- Produces: артефакт с адресом, который холст прототипов (задача 4) подключает как дизайн-систему; набор компонентов с именами, которые используют задачи 4–7.

- [ ] **Step 1:** `Artifact` `action: "quickstart"`, `intent: "other"` → создать артефакт из типа «Design System» с названием «Arcana Diary — дизайн-система» и выполнить инструкции типа (в них — формат файлов и `tokens.json` артефакта).
- [ ] **Step 2: Основа.** Цвета дня, ночи и мастей, шрифты и шкала, отступы, скругления, движение — значения ровно из `docs/design/tokens.json`.
- [ ] **Step 3: Логотип.** Надпись «Arcana Diary» (Cormorant Garamond 600) и знак-полумесяц (контурный, золото ночью, слива днём); вариант-иконка 32 × 32.
- [ ] **Step 4: Карта.** Рубашка: ночной фон, тонкая золотая рамка в два контура, полумесяц в центре. Лицо: скан, тонированный в синий с золотом SVG-фильтром (`feColorMatrix` в оттенки серого → `feComponentTransfer` таблицей от `#10163A` в тенях к `#E9D9B4` в светах), золотая рамка, номер римскими цифрами и название шрифтом Cormorant под изображением. Образцы — Луна, Солнце, Башня; каждая в размерах 700 × 1200 (масштабно) и 120 px высотой. Сканы загрузить как ассеты артефакта.
- [ ] **Step 5: Компоненты** (дневные и ночные варианты, где применимо): шапка с меню из 5 пунктов и EN | ES; подвал; хлебные крошки; кнопки — золотая (ночь), тёмная (день), контурная, текстовая; поле вопроса с подписью «Your question — optional»; чипы (ситуации, «1 card / 3 cards»); карта (рубашка, лицо, миниатюра); метка масти; блок ответа чтеца; вердикт «Yes / No / Not yet» со значком и словом; нижний лист «Save to your diary»; запись дневника; кнопки «Came true / Partly / No»; карточка «What Plus gives you»; состояние фокуса (золотая рамка 2 px).
- [ ] **Step 6: Точка утверждения.** Показать владельцу ссылку и спросить одно: утверждает ли дизайн-систему и вид карты (варианты: «да» / «правки: …»). Правки — внести и показать снова. Без «да» к задаче 4 не переходить.
- [ ] **Step 7:** если по правкам изменились значения — обновить `docs/design/tokens.json`, `python3 tools/design/tokens.py`, тесты задачи 2 зелёные, коммит `design(stage3): tokens updated after owner review`.

---

### Task 4: Холст прототипов — главная и ночная комната

**Files:** новый артефакт Claude Design (тип «Design») «Arcana Diary — прототипы» с подключённой дизайн-системой задачи 3.

- [ ] **Step 1:** создать холст из типа «Design» (title «Arcana Diary — прототипы»), подключить дизайн-систему задачи 3 по инструкции типа (установка в `project/ds/<folder>/`).
- [ ] **Step 2: Экран 1 — главная EN, телефон 390 × 844.** Шапка; надзаголовок «Free tarot reading»; заголовок «Ask the cards.»; строка «One question, three cards and an honest reading. No sign-up.»; поле вопроса (необязательное); три карты рубашкой; кнопка «Draw three cards»; строка «About 10 seconds · save it to your diary after»; ниже первого экрана — переходы к форматам (One card, Yes or No, Love, Card of the Day) и к значениям карт, карточка карты дня.
- [ ] **Step 3: Экран 2 — ночная комната, 5 кадров 390 × 844:** (а) касание кнопки, страница начинает гаснуть, панель растёт; (б) ночь на весь экран, три рубашки по центру; (в) первая карта перевёрнута; (г) все три перевёрнуты, подписи «Past · Present · Next step» и названия; (д) ответ чтеца: 3–4 коротких абзаца по запретам З1–З6, затем кнопки «Save to diary» (золотая) и «More about these cards» (контурная), строка «Ask another question».
- [ ] **Step 4: Точка утверждения.** Ссылка владельцу и один вопрос: «экраны 1–2 так?» (да / правки). Правки — внести; без «да» к задаче 5 не переходить.

---

### Task 5: Остальные экраны телефона (EN)

**Files:** тот же холст прототипов; по артборду на экран, 390 × 844 (длинные страницы — выше, по содержанию).

- [ ] **Step 1:** нижний лист «Save to your diary» поверх ответа: e-mail с подписью, «Continue with Google», «Continue with Apple», строка «Your reading stays here — nothing is lost».
- [ ] **Step 2:** дневник — список записей (дата, вопрос, три миниатюры, отметка «сбылось?») и одна запись с кнопками «Came true / Partly / No».
- [ ] **Step 3:** Yes or No — экран вопроса с чипами «1 card / 3 cards» и вердикт в ночи («No» крупно, значок, строка «Why: …», ссылка «The Moon — full meaning»).
- [ ] **Step 4:** Love — чипы ситуаций (Single, In a relationship, After a breakup, It's complicated), необязательные; кнопка «Draw for love».
- [ ] **Step 5:** Card of the Day — рубашка «Tap to turn your card» и перевёрнутая карта со значением на сегодня и «Remind me tomorrow».
- [ ] **Step 6:** страница карты «The Moon» — крошки Cards › Major Arcana › The Moon; карта; метка масти; ключевые слова; значение; раздел Reversed (запуск); разделы In love и As advice с пометкой «V1.1» (серым, только на макете); кнопка «Draw a card for your question» (открывает ночь на месте); соседние карты.
- [ ] **Step 7:** хаб 78 карт (блок старших арканов и четыре блока мастей с метками мастей, кнопка «Draw a card for your question») и страница старших арканов.
- [ ] **Step 8:** справочник «Yes or no» по картам (список с вердиктами, кнопка «Ask your question»).
- [ ] **Step 9:** карточка «What Plus gives you» (память чтеца, длинные расклады, вся история — без обещаний «узнать мысли другого») и страница 404 со ссылками на инструменты и хаб.

---

### Task 6: Испанские экраны и компьютер

- [ ] **Step 1: ES, телефон:** главная («Pregunta a las cartas.», формат «1 carta» внутри), Sí o no с вердиктом «Todavía no», страница «La Luna» (Cartas › Arcanos mayores › La Luna; разделы Invertida, En el amor, строка «¿Sí o no?»), «3 cartas» (крошки «Inicio › 3 cartas»).
- [ ] **Step 2: Компьютер 1440, EN:** главная, страница карты, хаб — как страницы (`expand: "fill"`, ширина по контейнеру); ночная комната на компьютере — по центру на затемнённом фоне, ширина сцены ≤ 960 px.

---

### Task 7: Кликабельные пути П1–П3

- [ ] **Step 1:** П1 — главная → ночь (кадры) → ответ → нижний лист → дневник; одним интерактивным артбордом с состоянием или артбордами со ссылками (`is_interactive: true`).
- [ ] **Step 2:** П2 — страница «The Moon» → «Draw a card for your question» → ночь на месте → ответ → «More about these cards» сворачивает ночь.
- [ ] **Step 3:** П3 — Yes or No → «Draw» → вердикт → «The Moon — full meaning».
- [ ] **Step 4:** пройти каждый путь кнопкой Play один раз и записать счёт действий до результата (для `00-design.md`).

---

### Task 8: Документы дизайна в репозитории

**Files:**
- Create: `docs/design/00-design.md`
- Create: `docs/design/analytics-events.md`

- [ ] **Step 1: `00-design.md`** — решения владельца (таблица из спецификации), ссылки на три артефакта (выбор направления, дизайн-система, прототипы), таблица путей П1–П8 со счётом действий (П1–П3 — по фактическому прохождению из задачи 7), список экранов прототипа с их статусом, вид карты и оговорка об издании колоды для этапа 4, правила для кода (подключить `tokens.css`; ночная комната — слой без адреса; `prefers-reduced-motion`).
- [ ] **Step 2: `analytics-events.md`** — таблица событий без cookie, по строке на событие: имя, когда срабатывает, параметры, вопрос, на который отвечает:

| Событие | Когда | Параметры |
|---|---|---|
| `tool_view` | открыта страница-инструмент | `tool` (home, one_card, yes_no, love, daily, three_cards), `lang` |
| `draw_click` | нажата «Вытянуть» | `tool`, `lang`, `has_question` (да/нет), `entry` (tool, card_page, hub) |
| `night_open` | ночь раскрылась | `tool`, `lang` |
| `cards_revealed` | все карты перевёрнуты | `tool`, `cards_count` |
| `reading_shown` | ответ чтеца показан | `tool`, `lang`, `ms_from_draw` |
| `save_click` | «Сохранить в дневник» | `tool`, `lang` |
| `signup_done` | вход завершён | `method` (email, google, apple) |
| `more_about_cards` | «Подробнее о картах» | `tool` |
| `outcome_answered` | ответ «сбылось?» | `after_days` (7, 30), `answer` (yes, partly, no) |
| `plus_view` | показана карточка Plus | `place` (limit, diary) |

  Ниже таблицы — воронка «tool_view → draw_click → reading_shown → save_click → signup_done» и правило: никаких текстов вопросов и личных данных в событиях.
- [ ] **Step 3: Commit**

```bash
cd ~/arcana-diary && git add docs/design/00-design.md docs/design/analytics-events.md && git commit -m "docs(stage3): design decisions, user paths and analytics events

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Проверка прототипов агентом Fable 5.2

**Files:** Create: `docs/design/review-fable.md`

- [ ] **Step 1:** запустить субагента на модели Fable 5.2 (`model: fable`), только чтение. Он получает: адреса холста прототипов и дизайн-системы, `docs/design/tokens.json`, раздел «Global Constraints» этого плана как чек-лист, спецификацию этапа 3 и антипримеры (`docs/research/stage1/30-opportunities.md`, раздел 2а). Моих выводов не получает. Задание: пройти П1–П3 и экраны задач 4–6; по каждому пункту чек-листа — выполнено / нарушено с указанием артборда; счёт действий по П1–П8; расхождения EN и ES; приоритет Critical / Important / Minor.
- [ ] **Step 2:** исправить Critical и Important на холсте; Minor — исправить или записать с причиной.
- [ ] **Step 3:** записать `docs/design/review-fable.md` — находки, что исправлено, что отложено и почему; коммит `docs(stage3): Fable review of prototypes and fixes`.

---

### Task 10: Журнал этапа и сдача

**Files:**
- Create: `docs/design/99-changelog.md`
- Modify: `docs/stages.md` (строка этапа 3, колонка «Состояние»)

- [ ] **Step 1: `99-changelog.md`** — версия 1.0 с датой; состав (артефакты и файлы); таблица ворот этапа 3 из спецификации (раздел 4) с состоянием и доказательством каждого; «Что осталось непроверенным» (вид карт на всех 78 — этап 4; поведение анимаций в коде — этап 4/6; проверка на людях снята решением владельца).
- [ ] **Step 2:** `docs/stages.md`, этап 3 — «выполнен в ветке `stage3-design`, <дата>; ждёт решения о слиянии».
- [ ] **Step 3:** итоговая проверка: `cd ~/arcana-diary/tools/design && ~/arcana-diary/api/.venv/bin/pytest -q` → `8 passed`; `cd ~/arcana-diary && python3 tools/design/tokens.py --check` → `OK`; `git status` чистый после коммита `docs(stage3): changelog and gates`.
- [ ] **Step 4:** superpowers:finishing-a-development-branch — варианты слияния владельцу.
