# Этап 1: семантика EN и ES — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Итоговые карты страниц `page-map-en.csv` и `page-map-es.csv` со всеми 12 типами страниц и записью TGA на каждый тип × язык, по методике гл. 7 «SEO Монстр 2027».

**Architecture:** Исследование, а не код. Каждая задача выдаёт артефакт в `docs/research/stage1/` и проверяется по чек-листу. Сбор данных Ahrefs идёт через MCP-инструменты `mcp__ab278b8f-…__*` (ответы большие — сбор по типам страниц делать в субагентах, в основной контекст возвращать только сводку). Единственный код — валидатор итоговой карты с тестами (Task 12).

**Tech Stack:** Ahrefs MCP (keywords-explorer-*, serp-overview, site-explorer-organic-keywords), curl для Reddit `.json`, Python 3.12 + pytest для валидатора, `~/seo-knowledge/tools/pdf_pages.py` для дословных форм книги.

Спецификация: `docs/superpowers/specs/2026-11-10-stage1-semantics-design.md`. Выжимка методики: `docs/research/stage1-method-brief.md`.

## Global Constraints

- Методика — книга 2027 гл. 7; формы брать дословно через `~/seo-knowledge/.venv/bin/python -I ~/seo-knowledge/tools/pdf_pages.py <стр>`; при расхождении с плейбуком верна книга.
- Рынки: EN → Ahrefs `country=US`; ES → `country=MX`, плюс отдельно `AR`, `CO`, `ES`, `US` для испанских формулировок. Объёмы разных стран не суммировать.
- Пустые данные — `нет данных`, не `0` (7.2.1). У каждого числа — страна и дата (`data_date`, ISO).
- Бюджет Ahrefs на этап — 100 000 юнитов. Каждый вызов записывается в `docs/research/stage1/corpus/ahrefs/ledger.csv` (поле `units-cost-total-actual` из ответа). При накопленных 80 000 — стоп и вопрос пользователю.
- В `select` Ahrefs запрашивать только нужные колонки: `keyword,volume,difficulty,parent_topic,intents` (traffic_potential и global_volume не брать — каждая по 10 юнитов на строку).
- 12 типов страниц и их ключи (`type_id`): `home`, `one-card`, `yes-no`, `love`, `cards`, `card-context`, `spreads`, `birth-card`, `horoscope`, `quiz`, `pairs`, `learn`.
- Запреты содержания (из плана продукта): предсказания здоровья, беременности, смерти, судов, слежка за третьими лицами, «снятие порчи».
- Коммит после каждой задачи командой `git add <файлы задачи> && git commit -m "<сообщение из задачи>" && git push`; где в задаче написано «Commit `<сообщение>` + push» — именно это. Сообщение заканчивается `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; `git push` после коммита.

## Карта файлов

| Файл | Задача |
|---|---|
| `docs/research/stage1/00-passport.md` | 1 |
| `docs/research/stage1/seeds.csv`, `corpus/ahrefs/ledger.csv` | 2 |
| `docs/research/stage1/cards.csv` | 2 |
| `corpus/ahrefs/us/<type_id>.csv`, `corpus/ahrefs/mx/<type_id>.csv` | 3, 4 |
| `corpus/ahrefs/es-by-country.csv` | 4 |
| `corpus/ahrefs/card-context-{us,mx}.csv` | 5 |
| `corpus/serp/{us,mx}/<slug>.json` | 6 |
| `corpus/reddit/questions.md`, `corpus/competitors.csv` | 7 |
| `10-task-map.md` | 8 |
| `20-groups-en.md`, `20-groups-es.md` | 9 |
| `30-opportunities.md` | 10 |
| `40-tga.md` | 11 |
| `tools/research/validate_page_map.py`, `tools/research/test_validate_page_map.py`, `page-map-{en,es}.csv` | 12 |
| `99-changelog.md` | 13 |

Все пути `corpus/…`, `10-…` и т. д. — внутри `docs/research/stage1/`.

---

### Task 1: Паспорт исследования

**Files:** Create `docs/research/stage1/00-passport.md`

- [ ] **Step 1: Получить дословный шаблон паспорта**

Run: `~/seo-knowledge/.venv/bin/python -I ~/seo-knowledge/tools/pdf_pages.py 573-576`
Expected: текст шаблона паспорта и стартового промпта (стр. 575).

- [ ] **Step 2: Заполнить паспорт по шаблону**

Источник фактов — документ плана https://claude.ai/artifact/PtJFSSX4C16tHKvTEqWM7R (разделы «Суть продукта», «Функции», «Сайт и страницы», «Платежи, право, этика»). Обязательные блоки в `00-passport.md` (заголовки — как в шаблоне книги; если шаблон требует другой набор, следовать шаблону):

- Цель как изменение в бизнесе: регистрации в дневник и заявки на Plus с поисковых входов, не «трафик».
- Рынки: EN — США; ES — Мексика основная, AR/CO/ES/US — проверочные.
- Аудитория — ситуации (не портреты): «спрашивает про отношения сегодня вечером», «нужен быстрый да/нет перед решением», «вытянула карту в чужом раскладе и ищет значение», «ежедневный ритуал».
- Границы: включено — 12 типов страниц; отложено — RU и 6 языков, `learn` (V3); исключено — сонники, нумерология, астрология как отдельный продукт (территория freudly).
- Решение владельца: объём 180 страниц к запуску, ~1 500 к неделе 13 — принимается как ограничение, исследование обосновывает каждый тип.
- Чего нельзя обещать: предсказания (см. запреты в Global Constraints); таро — инструмент размышления.
- Режим доказательности: три списка «установлено / не знаем / как проверим».
- Кто проверяет утверждения: значения карт — практикующий таролог (план продукта); SEO-решения — пользователь.

- [ ] **Step 3: Проверка**

Чек-лист: каждый блок шаблона стр. 573–574 заполнен или помечен «не установлено»; нет чисел спроса (они появятся в Task 3–5).

- [ ] **Step 4: Commit, push, показать пользователю**

```bash
cd ~/arcana-diary && git add docs/research/stage1/00-passport.md && git commit -m "research(stage1): research passport

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push
```
Пользователь утверждает паспорт до Task 8 (сбор данных Task 2–7 можно вести параллельно с ожиданием).

---

### Task 2: Стартовые ключи, список карт, учёт юнитов

**Files:** Create `docs/research/stage1/seeds.csv`, `docs/research/stage1/cards.csv`, `docs/research/stage1/corpus/ahrefs/ledger.csv`

- [ ] **Step 1: Учёт юнитов**

`corpus/ahrefs/ledger.csv`:
```
date,task,tool,country,params_short,rows,units
```

- [ ] **Step 2: Стартовые ключи — 5–8 на тип и рынок**

`seeds.csv`, колонки `type_id,market,seed`. Минимальный набор (дополнить до 5–8 вариантами из Ahrefs `search-suggestions`, если на тип меньше 5):

```
type_id,market,seed
home,US,tarot reading
home,US,free tarot reading
home,US,online tarot
home,US,ai tarot
home,US,tarot card reading
one-card,US,one card tarot
one-card,US,tarot card of the day
one-card,US,daily tarot
one-card,US,pull a tarot card
one-card,US,single card tarot reading
yes-no,US,yes or no tarot
yes-no,US,yes no tarot
yes-no,US,tarot yes or no question
yes-no,US,yes or no tarot reading free
yes-no,US,yes or no oracle
love,US,love tarot
love,US,love tarot reading
love,US,tarot love reading free
love,US,what does he think of me tarot
love,US,ex tarot reading
cards,US,tarot card meanings
cards,US,the moon tarot
cards,US,the tower tarot meaning
cards,US,three of swords meaning
cards,US,tarot cards list
card-context,US,the lovers tarot love
card-context,US,the star reversed
card-context,US,death tarot yes or no
card-context,US,the empress as feelings
card-context,US,the hermit advice
spreads,US,tarot spreads
spreads,US,celtic cross tarot
spreads,US,3 card tarot spread
spreads,US,love tarot spread
spreads,US,career tarot spread
birth-card,US,tarot birth card
birth-card,US,birth card tarot calculator
birth-card,US,what is my tarot card
birth-card,US,tarot card by birthday
birth-card,US,soul card tarot
horoscope,US,libra tarot
horoscope,US,tarot horoscope
horoscope,US,scorpio tarot reading
horoscope,US,weekly tarot horoscope
horoscope,US,zodiac tarot cards
quiz,US,what tarot card am i
quiz,US,tarot quiz
quiz,US,which tarot card are you
quiz,US,tarot personality test
quiz,US,tarot card quiz
pairs,US,tower and lovers tarot
pairs,US,tarot card combinations
pairs,US,death and the lovers tarot
pairs,US,tarot combinations meaning
pairs,US,the sun and the moon tarot
learn,US,how to read tarot cards
learn,US,tarot for beginners
learn,US,learn tarot
learn,US,how to read tarot
learn,US,tarot basics
home,MX,tarot
home,MX,tarot gratis
home,MX,lectura de tarot
home,MX,tarot online
home,MX,tirada de tarot
one-card,MX,carta del dia tarot
one-card,MX,tarot una carta
one-card,MX,tarot del dia
one-card,MX,saca una carta tarot
one-card,MX,tarot diario
yes-no,MX,tarot si o no
yes-no,MX,tarot sí o no gratis
yes-no,MX,tarot si o no amor
yes-no,MX,pregunta si o no tarot
yes-no,MX,oraculo si o no
love,MX,tarot del amor
love,MX,tarot amor
love,MX,tarot del amor gratis
love,MX,que siente por mi tarot
love,MX,tarot de pareja
cards,MX,significado de las cartas del tarot
cards,MX,la estrella tarot
cards,MX,la torre tarot
cards,MX,cartas del tarot y su significado
cards,MX,arcanos mayores
card-context,MX,la luna tarot amor
card-context,MX,la muerte tarot invertida
card-context,MX,el diablo tarot si o no
card-context,MX,los enamorados sentimientos
card-context,MX,el ermitaño consejo
spreads,MX,tiradas de tarot
spreads,MX,cruz celta tarot
spreads,MX,tirada de 3 cartas
spreads,MX,tirada de tarot amor
spreads,MX,tirada de tarot trabajo
birth-card,MX,carta del tarot segun fecha de nacimiento
birth-card,MX,arcano de nacimiento
birth-card,MX,cual es mi carta del tarot
birth-card,MX,arcano personal
birth-card,MX,carta de nacimiento tarot
horoscope,MX,tarot libra
horoscope,MX,tarot escorpio
horoscope,MX,horoscopo tarot
horoscope,MX,tarot semanal
horoscope,MX,tarot por signo
quiz,MX,que carta del tarot soy
quiz,MX,test de tarot
quiz,MX,que arcano soy
quiz,MX,test que carta eres
quiz,MX,quiz tarot
pairs,MX,combinaciones de cartas del tarot
pairs,MX,la torre y los enamorados
pairs,MX,combinacion de cartas tarot significado
pairs,MX,la muerte y el diablo tarot
pairs,MX,el sol y la luna tarot
learn,MX,como leer el tarot
learn,MX,aprender tarot
learn,MX,tarot para principiantes
learn,MX,curso de tarot
learn,MX,como tirar las cartas del tarot
```

- [ ] **Step 3: Список 78 карт**

`cards.csv`, колонки `card_id,arcana,suit,rank,name_en,slug_en,name_es,slug_es,es_variants`. Старшие арканы — 22 строки (`major-00-fool` … `major-21-world`), младшие — 56 (`wands-01-ace` … `pentacles-14-king`). ES-масти: Bastos, Copas, Espadas, Oros; в `es_variants` указать известные варианты (`Pentáculos` для Oros, `El Sumo Sacerdote` для El Hierofante, `La Rueda` для La Rueda de la Fortuna, `Sota` для Page). Проверка вариантов спроса — в Task 5.

Проверка: `python3 -c "import csv;r=list(csv.DictReader(open('docs/research/stage1/cards.csv')));print(len(r),len({x['card_id'] for x in r}))"` → `78 78`.

- [ ] **Step 4: Commit, push**

```bash
cd ~/arcana-diary && git add docs/research/stage1 && git commit -m "research(stage1): seeds, card list, units ledger

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push
```

---

### Task 3: Корпус EN (США)

**Files:** Create `corpus/ahrefs/us/<type_id>.csv` (12 файлов); Modify `corpus/ahrefs/ledger.csv`

Выполнять в субагенте (или по типу в отдельном субагенте), возвращать сводку: тип, число строк, сумма объёма топ-20, юниты.

- [ ] **Step 1: Замер стоимости на одном типе**

Для `yes-no`, US:
- `keywords-explorer-matching-terms`: `country=US`, `keywords=<seeds типа через запятую>`, `select=keyword,volume,difficulty,parent_topic,intents`, `where={"field":"volume","is":["gte",20]}`, `order_by=volume:desc`, `limit=150`.
- `keywords-explorer-related-terms`: те же `country`, `keywords`, `select`; `limit=50` (схему параметров взять через `doc` перед первым вызовом).
- `keywords-explorer-search-suggestions`: то же, `limit=50` (схема через `doc`).
Записать фактические `units-cost-total-actual` в ledger. Если сумма на тип > 3 500 юнитов — снизить `limit` matching до 100 и сообщить в сводке.

- [ ] **Step 2: Остальные 11 типов тем же способом**

Файл `corpus/ahrefs/us/<type_id>.csv`, колонки:
```
keyword,volume,difficulty,parent_topic,intent_flags,source_tool,country,data_date
```
`intent_flags` — перечень `true`-полей из `intents` через `|`; `source_tool` ∈ `matching|related|suggestions`; дубликаты по `keyword` внутри файла — одна строка, `source_tool` через `|`. `volume` пустой → `нет данных`.

- [ ] **Step 3: Проверка**

Run:
```bash
cd ~/arcana-diary/docs/research/stage1/corpus/ahrefs/us && for f in *.csv; do echo "$f $(($(wc -l < $f)-1))"; done && grep -c ',0,' *.csv
```
Expected: 12 файлов, в каждом ≥ 20 строк (кроме `learn`/`quiz` — допустимо меньше, отметить); `grep` по `,0,` — только реальные нули KD, не объёмы. Ledger: сумма юнитов задачи ≤ 30 000.

- [ ] **Step 4: Commit, push**

```bash
cd ~/arcana-diary && git add docs/research/stage1/corpus && git commit -m "research(stage1): EN corpus from Ahrefs (US)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push
```

---

### Task 4: Корпус ES (Мексика) и спрос по странам

**Files:** Create `corpus/ahrefs/mx/<type_id>.csv` (12), `corpus/ahrefs/es-by-country.csv`; Modify `ledger.csv`

- [ ] **Step 1: 12 типов по `country=MX`** — те же вызовы и формат файла, что в Task 3 Step 1–2.

- [ ] **Step 2: Список для проверки по странам**

Из всех `mx/*.csv` взять 200 ключей с наибольшим `volume` (без `нет данных`).

- [ ] **Step 3: Спрос по странам**

`keywords-explorer-overview` (схема через `doc`) — 4 вызова, по одному на `country` ∈ `AR`, `CO`, `ES`, `US`, `keywords=<200 ключей через запятую>`, `select=keyword,volume,difficulty`. Записать `es-by-country.csv`:
```
keyword,volume_mx,volume_ar,volume_co,volume_es,volume_us_es,data_date
```
Отсутствующий ключ в ответе страны → `нет данных`.

- [ ] **Step 4: Проверка**

200 строк; ни одна ячейка объёма не `0` там, где страна ключ не вернула; ledger: сумма задачи ≤ 35 000.

- [ ] **Step 5: Commit, push** — `git add docs/research/stage1/corpus && git commit -m "research(stage1): ES corpus (MX) and per-country demand"` (с trailer из Global Constraints) и `git push`.

---

### Task 5: Матрица «карта × контекст»

**Files:** Create `corpus/ahrefs/card-context-us.csv`, `corpus/ahrefs/card-context-mx.csv`; Modify `ledger.csv`

- [ ] **Step 1: Сгенерировать формулировки из `cards.csv`**

EN, 6 на карту (78 × 6 = 468): `<name> tarot`, `<name> tarot love`, `<name> yes or no`, `<name> reversed`, `<name> as feelings`, `<name> advice` (`<name>` в нижнем регистре, без артикля для младших: `three of swords`).
ES, 6 на карту: `<nombre> tarot`, `<nombre> tarot amor`, `<nombre> si o no`, `<nombre> invertida`, `<nombre> sentimientos`, `<nombre> consejo` + для карт с `es_variants` — те же 6 с вариантом.

- [ ] **Step 2: Объёмы**

`keywords-explorer-overview`, `country=US` (EN) и `country=MX` (ES), пачками по 100 ключей, `select=keyword,volume,difficulty,parent_topic`. Файл:
```
card_id,context,keyword,volume,difficulty,parent_topic,country,data_date
```
`context` ∈ `base|love|yes-no|reversed|feelings|advice`.

- [ ] **Step 3: Сводка**

Внизу каждого файла не писать; вместо этого в сводке субагента: по каждому `context` — число карт с `volume ≥ 50`, медиана объёма; по ES — какой вариант названия масти/карты побеждает (Oros vs Pentáculos и т. д.). Сводку вставить в `20-groups-*.md` в Task 9.

- [ ] **Step 4: Проверка и commit**

468 строк EN; ES ≥ 468; ledger: сумма задачи ≤ 20 000. Commit `research(stage1): card × context demand matrix` + push.

---

### Task 6: Снимки выдачи

**Files:** Create `corpus/serp/queries.csv`, `corpus/serp/us/<slug>.json`, `corpus/serp/mx/<slug>.json` (~72); Modify `ledger.csv`

- [ ] **Step 1: Выбор запросов** — 3 на тип × рынок: самый объёмный из `<market>/<type_id>.csv` и два с другим модификатором (разные `parent_topic`). Записать в `corpus/serp/queries.csv` (`type_id,market,query,reason`).

- [ ] **Step 2: Снять** — `serp-overview`, `keyword=<запрос>`, `country=US|MX`, `top_positions=10`, `select=position,url,title,type,domain_rating,traffic,page_type,update_date`. Сохранить как есть в JSON с полями-обёрткой:
```json
{"query": "...", "country": "US", "taken_at": "2026-11-11", "source": "ahrefs serp-overview", "positions": [...]}
```
`slug` — запрос в нижнем регистре, пробелы → `-`.

- [ ] **Step 3: Проверка** — ~72 файла; в каждом `positions` непустой, `update_date` есть; органика отличима от спецблоков по `type`. Ledger: ≤ 10 000. Commit `research(stage1): SERP snapshots US/MX` + push.

---

### Task 7: Голос аудитории и конкуренты

**Files:** Create `corpus/reddit/questions.md`, `corpus/competitors.csv`; Modify `ledger.csv`

- [ ] **Step 1: Reddit (EN)**

Run (по одному сабреддиту):
```bash
curl -s -A "arcana-research/0.1" "https://www.reddit.com/r/tarot/top.json?t=year&limit=100" -o "$SCRATCH/reddit-tarot.json"   # SCRATCH=/tmp/claude-1000/-home-deploy/0ce1087d-69eb-43d4-8c76-3ce3133aa869/scratchpad; сырые ответы в репозиторий не кладём
```
Повторить для `r/TarotReadings`, `r/tarot/search.json?q=yes%20or%20no&restrict_sr=1&limit=100`, `…q=what%20does%20he%20feel`. Если Reddit отвечает 403/429 — использовать WebFetch на те же URL. В `questions.md` — минимум 50 записей формата:
```
- «<исходная фраза>» — <ссылка>, <дата поста>; ситуация: <одна строка>; тип: <type_id или «вне»>
```
Оригинал и пересказ раздельно (стр. 582–583).

- [ ] **Step 2: Конкуренты**

Выбрать по 3–4 на язык из снимков Task 6: часто встречающиеся в топ-10 домены с `domain_rating` ≤ 40 (быстрорастущие, как в плане: tarotap, juliantarot, nostra-tarot, tellmytarot — проверить, кто реально в выдаче). Для каждого: `site-explorer-top-pages` (`limit=50`, схема через `doc`) и `site-explorer-organic-keywords` (`country` рынка, `limit=200`, `select` — ключ, объём, позиция, URL). `competitors.csv`:
```
domain,market,url,keyword,volume,position,page_role_guess,data_date
```
`page_role_guess` — наш `type_id`, к которому относится страница конкурента, или `вне`.

- [ ] **Step 3: Проверка и commit** — ≥ 50 вопросов; ≥ 6 доменов; ledger: ≤ 15 000. Commit `research(stage1): audience questions and competitor pages` + push.

---

### Task 8: Карта задач и исключений

**Files:** Create `docs/research/stage1/10-task-map.md`

Требует утверждённого паспорта (Task 1).

- [ ] **Step 1: Дословные шаблоны** — `pdf_pages.py 593-601` (модификаторы стр. 596, критерий vs ограничение стр. 596, карта задач стр. 600–601, запрещённое утверждение стр. 600).

- [ ] **Step 2: Заполнить по каждому из 12 типов, отдельно EN и ES** — уровни сущность → задача → формулировка (формулировки — из корпуса Task 3–7 с указанием файла); поля шаблона стр. 600–601; модификаторы — до очистки; скрытые задачи — по 4 направлениям (уточнение свойств, замены, дополнения, расширение сценария) с тестом «что изменится, если вопрос убрать». Отдельный раздел «Исключения и запрещённые утверждения» по запретам из Global Constraints и с примерами формулировок из корпуса, которые попадают под запрет (например, «will I get pregnant tarot»).

- [ ] **Step 3: Проверка** — у каждой задачи есть «чем подтверждено» со ссылкой на файл корпуса; ни одна формулировка без источника. Commit `research(stage1): task and exclusion map` + push.

---

### Task 9: Группы по выдаче

**Files:** Create `docs/research/stage1/20-groups-en.md`, `docs/research/stage1/20-groups-es.md`

- [ ] **Step 1: Дословный промпт и формы** — `pdf_pages.py 602-609` (предварительная группировка 602–603, протокол выдачи 604–605, аудит машинной кластеризации 607–608, промпт `/кластеры` 608–609, запись итога группы 609).

- [ ] **Step 2: Предварительные группы** — по промпту `/кластеры` на формулировках карты задач (300–500 запросов на прогон, по плейбуку шаг 2), отдельно EN и ES.

- [ ] **Step 3: Проверка групп по снимкам Task 6** — сравнивать документы (URL), а не домены; органику отдельно от спецблоков; края больших групп; 4 типа ошибок (объединено лишнее, разделено одно и то же, пропало уточнение, ложная определённость). Вставить сводку матрицы Task 5.

- [ ] **Step 4: Запись итога по каждой группе** по форме стр. 609 + список неопределённых запросов.

- [ ] **Step 5: Второй прогон** — независимая проверка на смешение интентов (новый субагент без доступа к выводам первого, только к корпусу и группам), расхождения — в раздел «Спорные группы» с решением.

- [ ] **Step 6: Commit** `research(stage1): SERP-verified groups EN/ES` + push.

---

### Task 10: Карточки возможностей

**Files:** Create `docs/research/stage1/30-opportunities.md`

- [ ] **Step 1** — `pdf_pages.py 610-619` (полнота получения страницы 612–614, отрицательный вывод 614–616, 4 вопроса отличия 616, карточка 618, `/контентные-пробелы` 619).
- [ ] **Step 2** — сопоставить три корпуса: аудитория (`reddit/questions.md`, карта задач), наш сайт (план продукта: 4 отличия — чтец с памятью, «сбылось?», расклад на двоих, бот), конкуренты (`competitors.csv`). Уровни проверки функций конкурента: заявлена / найдена и доступна / проверена на сценарии.
- [ ] **Step 3** — карточки «Возможность → Основание → Предложение → Что неизвестно → Проверка → Ограничение», минимум по одной на тип страницы запуска.
- [ ] **Step 4** — commit `research(stage1): opportunity cards` + push.

---

### Task 11: Решения TGA

**Files:** Create `docs/research/stage1/40-tga.md`

- [ ] **Step 1** — `pdf_pages.py 620-629` (условия 620–621, развилка форм 622–624, пробное встраивание и тест удаления 624–625, таблица неопределённостей 627, оспаривание 628, запись решения 629).
- [ ] **Step 2** — 24 записи (12 типов × EN/ES) по форме стр. 629: Решение → Основание (ссылки на группы, снимки, карточки) → Альтернатива и когда к ней вернуться → Перед написанием → Граница. Для `card-context` — отдельное доказательство по каждому из 5 модификаторов (меняет ли задачу и план ответа), на данных матрицы Task 5; модификатор, не прошедший проверку, получает альтернативную форму (раздел на странице карты) — но объём страниц по решению владельца сохраняется: в записи явно указать конфликт и риск.
- [ ] **Step 3** — тест «Человек откроет эту страницу, чтобы…» и «Чего пользователь не получит из существующего документа?» — ответ в каждой записи.
- [ ] **Step 4** — commit `research(stage1): TGA decisions per page type` + push.

---

### Task 12: Итоговая карта и валидатор

**Files:**
- Create: `tools/research/validate_page_map.py`, `tools/research/test_validate_page_map.py`
- Create: `docs/research/stage1/page-map-en.csv`, `docs/research/stage1/page-map-es.csv`

**Interfaces:**
- Produces: `validate(path: str, lang: str) -> list[str]` (пустой список = карта корректна); CLI `python3 tools/research/validate_page_map.py <path> <en|es>` → код выхода 0/1.

- [ ] **Step 1: Падающие тесты**

`tools/research/test_validate_page_map.py`:
```python
import csv
from pathlib import Path

from validate_page_map import COLUMNS_EN, COLUMNS_ES, validate


def write(tmp_path: Path, lang: str, rows: list[dict]) -> str:
    cols = COLUMNS_EN if lang == "en" else COLUMNS_ES
    p = tmp_path / f"map-{lang}.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "нет данных") for c in cols})
    return str(p)


def good_row(**over) -> dict:
    row = {
        "id": "en-001", "page_type": "yes-no", "working_title": "Yes or No Tarot",
        "task": "решает да/нет → перед решением → проверить знак карты → короткий ответ с причиной",
        "intent_label": "информационный", "top_entities": "tarot|yes or no|card",
        "queries": "yes or no tarot", "volume_us": "41000", "kd": "60", "data_date": "2026-11-11",
        "decision": "самостоятельная страница", "rationale": "40-tga.md#yes-no-en",
        "priority_value": "высокий", "priority_readiness": "средний", "priority_constraints": "нет",
        "maintenance_cost": "неизвестно", "dependencies": "нет", "open_questions": "нет", "wave": "запуск",
    }
    row.update(over)
    return row


def test_good_map_passes(tmp_path):
    assert validate(write(tmp_path, "en", [good_row()]), "en") == []


def test_zero_volume_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(volume_us="0")]), "en")
    assert any("нет данных" in e for e in errs)


def test_duplicate_id_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(), good_row()]), "en")
    assert any("id" in e for e in errs)


def test_unknown_decision_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(decision="сделать")]), "en")
    assert any("decision" in e for e in errs)


def test_volume_without_date_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(data_date="")]), "en")
    assert any("data_date" in e for e in errs)


def test_es_requires_country_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text(",".join(COLUMNS_EN) + "\n")
    errs = validate(str(p), "es")
    assert any("колонк" in e for e in errs)
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate_page_map'`.

- [ ] **Step 2: Реализация**

`tools/research/validate_page_map.py`:
```python
"""Проверка итоговой карты страниц этапа 1 (колонки — спецификация этапа 1)."""
import csv
import sys

COMMON_HEAD = ["id", "page_type", "working_title", "task", "intent_label", "top_entities", "queries"]
COMMON_TAIL = ["kd", "data_date", "decision", "rationale", "priority_value", "priority_readiness",
               "priority_constraints", "maintenance_cost", "dependencies", "open_questions", "wave"]
COLUMNS_EN = COMMON_HEAD + ["volume_us"] + COMMON_TAIL
COLUMNS_ES = COMMON_HEAD + ["volume_mx", "volume_ar", "volume_co", "volume_es", "volume_us_es"] + COMMON_TAIL

PAGE_TYPES = {"home", "one-card", "yes-no", "love", "cards", "card-context", "spreads",
              "birth-card", "horoscope", "quiz", "pairs", "learn"}
DECISIONS = {"доработать", "раздел", "имеющийся ответ", "самостоятельная страница", "отклонить", "получить данные"}
WAVES = {"запуск", "V1.1", "V2", "V3"}
NO_DATA = "нет данных"


def validate(path: str, lang: str) -> list[str]:
    expected = COLUMNS_EN if lang == "en" else COLUMNS_ES
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != expected:
            return [f"колонки не совпадают: ожидалось {expected}, получено {header}"]
        rows = list(reader)

    errors: list[str] = []
    volume_cols = [c for c in expected if c.startswith("volume_")]
    seen: set[str] = set()
    for n, row in enumerate(rows, start=2):
        rid = row["id"]
        if rid in seen:
            errors.append(f"строка {n}: повтор id {rid}")
        seen.add(rid)
        if row["page_type"] not in PAGE_TYPES:
            errors.append(f"строка {n}: неизвестный page_type {row['page_type']}")
        if row["decision"] not in DECISIONS:
            errors.append(f"строка {n}: неизвестный decision {row['decision']}")
        if row["wave"] not in WAVES:
            errors.append(f"строка {n}: неизвестный wave {row['wave']}")
        has_volume = False
        for c in volume_cols:
            v = row[c].strip()
            if v == "0":
                errors.append(f"строка {n}: {c}=0 — для отсутствия данных писать «{NO_DATA}»")
            elif v and v != NO_DATA:
                if not v.isdigit():
                    errors.append(f"строка {n}: {c} не число: {v}")
                has_volume = True
        if has_volume and not row["data_date"].strip():
            errors.append(f"строка {n}: есть объём, но пустой data_date")
        for c in ("task", "rationale"):
            if not row[c].strip() or row[c] == NO_DATA:
                errors.append(f"строка {n}: пустое {c}")
    return errors


if __name__ == "__main__":
    errs = validate(sys.argv[1], sys.argv[2])
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    sys.exit(1 if errs else 0)
```

- [ ] **Step 3: Тесты проходят**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `6 passed`.

- [ ] **Step 4: Commit валидатора** — `git add tools/research && git commit -m "feat(research): page map validator with tests"` (с trailer) + push.

- [ ] **Step 5: Собрать карты** — `pdf_pages.py 659-666` (итоговая карта 659–660, зависимости 662, состояние утверждения 663). По одной строке на каждую страницу/шаблон-строку: для `cards` — 78 строк + хаб; для `card-context` — по строке на модификатор (с объёмами — медиана по матрице Task 5 в `volume_*`, точные объёмы — в матрице); для `horoscope` — 12; остальные — по страницам из записей TGA. Отклонённые кандидаты — тоже строками с `decision=отклонить` и причиной в `rationale`.

- [ ] **Step 6: Валидация**

Run:
```bash
cd ~/arcana-diary && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es
```
Expected: `OK` дважды.

- [ ] **Step 7: Commit** `research(stage1): final page maps EN/ES` + push.

---

### Task 13: Ворота этапа и журнал

**Files:** Create `docs/research/stage1/99-changelog.md`

- [ ] **Step 1: Проверка ворот** (из спецификации), с доказательством на каждый пункт:
  - 24 записи в `40-tga.md` — `grep -c '^### ' docs/research/stage1/40-tga.md` → ≥ 24;
  - второй прогон групп — раздел «Спорные группы» в `20-groups-*.md` заполнен;
  - страницы `wave=запуск`: в карте у каждой ≥ 10 сущностей в `top_entities` (через `|`) и ≥ 10 интентов в записи группы — посчитать скриптом `python3 -c` по CSV;
  - объёмы с датой — валидатор `OK`;
  - открытые вопросы — в колонке `open_questions`, не в общих заметках;
  - сумма юнитов в ledger ≤ 100 000.
- [ ] **Step 2: Журнал** — `99-changelog.md`: версия 1.0, дата, ответственный, состав, изменения.
- [ ] **Step 3: Commit, push, отчёт пользователю** — по формату ТЗ (раздел 8): сначала вывод, потом решения по типам с источниками, отдельным списком — не проверенное и вопросы. Пользователь просматривает `40-tga.md` и карты.

---

## Поправка 1 (10.11.2026): двухшаговый сбор Ahrefs

**Причина.** Замер 10.11.2026: стоимость строки Ahrefs зависит от колонок — `keyword` ≈ 1 юнит, `volume` +10,
`difficulty` +10, `parent_topic` +11. Полный набор колонок по плану давал 8 000 юнитов на тип × рынок (> 200 000
на этап). Книга: частотность ≠ важность (7.2.1), смена формулировки без смены задачи — не новая задача (c07.07):
для карты задач нужна широта формулировок, а не длинный хвост с цифрами.

**Заменяет** в Task 3, 4, 5 параметры `select`, лимиты и формат файлов; остальное в задачах без изменений.

**Шаг A — разведка формулировок (≈1 юнит/строка).** Для каждого типа × рынка: `matching-terms` по 5 сидам типа,
`select=keyword`, `order_by=volume:desc`, `limit=300`; `related-terms` и `search-suggestions` — `select=keyword`,
`limit=100` (параметры через `doc`). Один раз на рынок: `matching-terms`, `keywords=tarot` (MX: `tarot`),
`terms=questions`, `select=keyword`, `order_by=volume:desc`, `limit=300`. Без `where`. Файл
`corpus/ahrefs/<us|mx>/discovery/<type_id>.csv` и `…/discovery/questions.csv`: `rank,keyword,source_tool,country,data_date`
(`rank` — порядковый номер в ответе, т. е. по убыванию спроса).

**Шаг B — «верхушка» с объёмом (≈11 юнитов/строка).** Список на оценку: по каждому типу первые 60 из matching +
первые 20 из related + первые 20 из suggestions; плюс первые 100 вопросов; без повторов по всему рынку.
`keywords-explorer-overview`, `select=keyword,volume`, пачками по 100. Файл `corpus/ahrefs/<us|mx>/<type_id>.csv`:
`keyword,volume,source_tool,country,data_date` (запрос встречается у нескольких типов — строка в каждом файле
типа, объём один). Нет в ответе → `нет данных`.

**KD** не собирается в Task 3–5; добирается в Task 12 через `overview` (`select=keyword,difficulty`) только для
основных запросов строк карты со `wave=запуск`.

**Матрица Task 5:** `select=keyword,volume` (без `difficulty`, `parent_topic`); колонки файла
`card_id,context,keyword,volume,country,data_date`. ES-варианты дополнить: El Ahorcado, La Fortaleza,
La Temperancia, La Parca, El Papa, El Eremita, El Carruaje (по 6 формулировок на вариант).

**Task 4, спрос по странам:** 100 верхних ES-запросов вместо 200; `select=keyword,volume`.

**Лимиты:** Task 3 ≤ 15 000; Task 4 ≤ 20 000; Task 5 ≤ 12 000; этап ≤ 100 000 без изменений.
Уже оплаченная выгрузка yes-no (US) с полным набором колонок —
`~/.claude/projects/-home-deploy/0ce1087d-69eb-43d4-8c76-3ce3133aa869/tool-results/toolu_01B45DE7kJLkzUKa7rmJjXeY.json`
— используется для Шага A и B типа `yes-no` вместо повторного запроса matching.

## Поправка 2 (10.11.2026): верхушка с объёмом за один проход

**Причина.** Уточнённый замер: сортировка `order_by=volume` тарифицируется как колонка `volume` (+10/строка);
`select=keyword` без сортировки — 1/строка, но без порядка по спросу (мусор). `parent_topic` ≈ +1/строка
(в первом замере 12 = 1 + 10 за сортировку + 1). Шаги A и B поправки 1 объединяются.

**Заменяет шаги A и B поправки 1.** На каждый тип × рынок: `matching-terms` `limit=60`, `related-terms` `limit=15`,
`search-suggestions` `limit=15`; все — `select=keyword,volume,parent_topic`, `order_by=volume:desc`. Вопросы: один
вызов на рынок, `terms=questions`, `limit=100`, те же `select` и сортировка. Файл `corpus/ahrefs/<us|mx>/<type_id>.csv`:
`rank,keyword,volume,parent_topic,source_tool,country,data_date`; вопросы — `…/questions.csv`. Каталог `discovery/`
не используется (уже собранный `us/discovery/home.csv` хранится как есть, для `home` matching перезапрашивать
`limit=60` с объёмом).

**Лимиты:** Task 3 ≤ 17 000 новых юнитов (сверх уже потраченных 8 230); Task 4 ≤ 18 000; Task 5 ≤ 12 000.
