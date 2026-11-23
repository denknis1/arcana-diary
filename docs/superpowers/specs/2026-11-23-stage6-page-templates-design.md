# Этап 6: шаблоны страниц для текстов этапа 5 — дизайн

Дата: 23.11.2026. Основа: тексты этапа 5 (`content/cards/pages/{en,es}/*.json` схема 2 + `template-strings.json`;
`content/pages/{en,es}/*.json`), правила `docs/research/stage5/30-card-page-rules.md` (§12 — что делает этап 6),
план `docs/research/stage5/50-tools-page-plan.md`, прототипы этапа 3 (канвас https://claude.ai/artifact/6X29CmJr5dEU75KGcBBZuP:
CardMoon, DeskCard, Hub, DeskHub, Major, YesNoList, TresCartas, LaLuna; копии — `docs/design/prototypes/`;
тексты прототипов устарели — берём из них только раскладку и стиль; «стихии» мастей и «Siguiente paso» не переносим), дизайн-система
`docs/design/00-design.md` + `tokens.css`, структура этапа 2 (`docs/research/stage2/links-{en,es}.csv`,
`hreflang.csv`, карты страниц этапа 1). Решения владельца 23.11.2026 — формами (34–36).

## 1. Решения владельца

34. Этап 6 — одна спецификация и один план из 5 частей; после каждой части — выкладка на стенд по слову владельца и
    его просмотр.
35. Служебные страницы собираются, но **скрыты**, пока в них есть метки оператора: `noindex`, нет в меню, подвале и
    карте сайта; на открытый сайт (после запуска) с меткой сборка не проходит.
36. Цифры лимитов и счётчики вердиктов подставляются **при сборке** из кода сервера и данных колоды.

## 2. Как данные попадают на сайт

- `tools/site/sync_site_data.py` (уже копирует колоду и значения в `site/src/data/`, есть `--check`) копирует ещё:
  страницы карт и `template-strings.json` → `site/src/data/cardpages/`, страницы `content/pages` →
  `site/src/data/pages/`, и пишет `site/src/data/facts.json`: `guest_limit`, `user_limit`, `followups`, `diary_free`
  (читает константы `DAILY_LIMIT`, `USER_DAILY_LIMIT`, `FOLLOWUP_LIMIT`, `FREE_DIARY_VISIBLE` из
  `api/app/config.py` разбором текста, без импорта), `yes_count`, `no_count`, `unclear_count` (из `deck.json`),
  `editor_name` = «Adrian Solenne». Метки оператора (`operator_name` и др.) в `facts.json` не попадают — пока их нет.
- `site/src/lib/facts.ts` — `fill(text, facts)`; страница с меткой, которой нет в `facts.json`, помечается
  `hidden` (только служебные); проверка сборки падает, если метка `{…}` осталась на не скрытой странице.

## 3. Часть 1 — фундамент (все страницы)

- **`<head>`** (`Base.astro` получает `description`, `image?`, `jsonLd?`, `alternates`): meta description;
  canonical `https://arcanadiary.com{path}`; `hreflang` en/es по `pairs.json` + `x-default` = EN; страница без пары
  — только своя ссылка; Open Graph и Twitter (title, description, url, image — скан карты на странице карты, иначе
  общая картинка); `noindex` как сейчас + скрытые служебные.
- **JSON-LD** (`site/src/lib/jsonld.ts`): `BreadcrumbList` везде, где есть крошки; `FAQPage` из `faq`; страница
  карты — `Article` (headline = h1, `author` и `publisher` — Organization «Arcana Diary», `dateModified` =
  `reviewed_at`, `reviewedBy` — Person `{editor_name}` с ролью editor, `image` — скан, `isBasedOn` — Wikisource
  Уэйта); хабы — `CollectionPage` + `ItemList`; инструменты — `WebPage`.
- **Крошки** (`site/src/lib/breadcrumbs.ts`, первым — Home / Inicio): старшая карта — Home › Cards › Major Arcana ›
  Карта; младшая — Home › Cards › Карта; старшие арканы — Home › Cards › Major Arcana; хаб — Home › Cards;
  справочник да/нет — Home › Yes or No › Card list; «3 cartas» — Inicio › 3 cartas; инструменты на главной — без
  крошек; служебные — Home › Страница.
- **Меню**: пункт «Card Meanings» / «Significados» (`/cards`, `/es/cartas`) по прототипу; **подвал**: About, How our
  readings work, Contact, Privacy, Terms (ES-пары) — только не скрытые.
- **Карта сайта** `sitemap.xml` — своим кодом при сборке (без новых пакетов): все индексируемые страницы с
  `xhtml:link` hreflang; `robots.txt` получает строку `Sitemap:`. Скрытые и `noindex` — вне карты.
- **Адреса**: в `routes.ts` — новые `PageKey` и пути (§4–§6), `allPagePaths()` растёт; пары hreflang для
  служебных страниц добавить в `hreflang.csv` (en↔es) и в `pairs.json`. Проверить конфликт «файл/папка»
  (`/cards` и `cards/…`, `/yes-no` и `yes-no/cards`, `/es/cartas` и `es/cartas/…`) в
  `deploy/test-site-routes.sh`.

## 4. Часть 2 — страница карты (78 × 2)

По прототипу CardMoon (телефон) и DeskCard (компьютер, две колонки: скан и CTA слева, текст справа) и §12 правил:
крошки → скан 1909 (`image_alt`, подпись шаблона) + строка фактов + H1 + капсула + таблица ключевых слов → ссылки
«на этой странице» (чипы к разделам) → 12 блоков по порядку с заголовками; в блоке `waite` — цитата
`<blockquote lang="en">` с подписью и страницами, перевод (ES, «Traducción nuestra»), строка о тяжёлых словах при
`harsh`, граница «дальше — современное чтение»; `work_money` + строка о деньгах; `yes_no` — сборка «Upright: … /
Reversed: Not clear yet / правило» из данных; `in_a_reading` + оговорка; `combinations` — таблица пар со ссылками;
`ask_yourself` — список → CTA «Draw {card} for your question» (существующий `ReadingIsland`, без изменений логики)
→ FAQ (`<details>`, первый открыт) → соседние карты (`related`, ссылки) → «About this page» (источники из `sources`,
метод с `{editor_name}` и `reviewed_at`, заметка о колоде). `mentions` — ссылка на первое упоминание карты в тексте.
Заменяет временный `CardView.astro` по тем же адресам; ES — `/es/cartas/<slug_es>`.

## 5. Часть 3 — инструменты и хабы

- Инструменты (главная, one-card, daily, yes-no, love; ES home, carta-del-dia, si-o-no, amor): над инструментом
  — надпись над заголовком из словаря, H1 и lead из текста страницы; под инструментом — блоки и FAQ из
  `content/pages`. title/description — из текста страницы.
- Новые: `/es/tiradas/3-cartas` — инструмент на 3 карты (существующий `ReadingIsland`, режим трёх карт, событие
  `three_cards` уже в схеме) + текст; `/cards` и `/es/cartas` — капсула, сетка старших и списки мастей по прототипу
  Hub/DeskHub (**без стихий** — решение 10), блоки и FAQ; `/cards/major-arcana` и `/es/cartas/arcanos-mayores` —
  капсула, список 22 с ключевым словом из значений, блоки, FAQ; `/yes-no/cards` — капсула, правило, списки «да / нет
  / пока неясно» по `deck.json` со ссылками на карты, блоки, FAQ. Списки карт — из данных, не из текста.

## 6. Часть 4 — служебные страницы

Шаблон текста (H1, lead, блоки, FAQ если есть) для 10 страниц; скрыты по §2. Ссылки на политику у строки поставщика
ИИ (подэтап 4.9) и в согласии — появляются вместе с открытием страницы.

## 7. Часть 5 — перелинковка и аудит

- Ссылки строк `links-{en,es}.csv` волны «запуск»: шаблонные (`@drawn`, `@same-card`, `@neighbors`, `@cards`,
  `@major`, `@minor`, `@diary`) делает шаблон; адресные — в блоках страниц, с текстом ссылки по `anchor_pattern`
  и терминами контекста рядом. Скрипт `tools/site/check_links.py` по собранному `site/dist` проверяет каждую строку
  волны «запуск»: ссылка есть, ведёт на нужный адрес, текст ссылки по шаблону.
- Аудит семантической вёрстки (скилл semanticrank) по 6 страницам (карта EN/ES, хаб, старшие, да/нет, главная ES)
  → правки шаблонов.

## 8. Проверка

- vitest: `facts.fill`, крошки, JSON-LD, hreflang/canonical, сборка блоков карты (по 2–3 картам), скрытие служебных.
- `tools/site/check_dist.py` расширить: все ожидаемые страницы; на каждой — title, description, canonical, hreflang
  (по паре), JSON-LD разбирается; нет `{меток}` на не скрытых; скрытые — `noindex` и вне `sitemap.xml`; число
  страниц. `deploy/test-site-routes.sh` — новые адреса и конфликт «файл/папка».
- API не меняется (кроме чтения констант скриптом). Проверка ветки — Sonnet; финальная — Fable (по желанию
  владельца). Слияние и выкладка — по слову владельца после каждой части.

## 9. Вне этапа 6

Подключение почтового сервиса, данные оператора, сверка телефонов помощи, снятие закрытия стенда (этап 7).
