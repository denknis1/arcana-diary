# Группы по выдаче: Arcana Diary, ES (Мексика)

Версия 1.0, 11.11.2026. Метод — «SEO Монстр 2027», 7.5 (стр. 602–609), как в `20-groups-en.md`: предварительная
группировка от карты задач (стр. 602–603), сравнение документов, а не доменов, органика отдельно от спецблоков
(стр. 604–605), уточняющие запросы и смешанная выдача (стр. 605–607), четыре типа ошибок (стр. 608), поля записи
итога (стр. 609). Формулировки книги не переносились — использованы её поля.

## Как читать

- **Спрос:** число в скобках — Ahrefs Keywords Explorer, страна Мексика, 10.11.2026 (`corpus/ahrefs/mx/<тип>.csv`,
  `corpus/ahrefs/card-context-mx.csv`; другой файл назван рядом). `нет данных` — Ahrefs не вернул запрос; `0` —
  спрос ниже порога. Группировка — только по данным MX.
- **Справочно по странам** — `corpus/ahrefs/es-by-country.csv` (10.11.2026), колонки AR, CO, ES, US-ES; объёмы
  стран не складываются и на состав групп не влияют. Есть только для 97 верхних запросов MX; для остальных —
  `нет данных`.
- **Снимки выдачи:** Ahrefs `serp-overview`, Мексика, топ-10 позиций, без трафика; Task 6 — 10.11.2026, Task 9 —
  11.11.2026 (`corpus/serp/queries.csv`); файл — `corpus/serp/mx/<slug>.json`. Снимки с пометкой
  `stale_serp` (`tarot diario` — 2024-01, `tarot una carta` — 2022-01, `tarot si o no amigo` — 2024-03) для
  проверки групп не используются; `empty_serp` — Ahrefs вернул пустую выдачу, файла нет.
- **Органика и пересечение** — как в EN: `'organic' in type`, позиции 1–10, без `*_sitelink`; URL без схемы,
  `www.`, хвостового `/`, якоря и параметра `?tl=`/`?hl=`. Совпадение доменов отмечено отдельно и совпадением не
  считается.
- **Просмотр документов:** по URL, заголовку и `page_type` Ahrefs (предположение модели). Страницы MX не
  открывались — решения, которые от этого зависят, помечены.
- **Статус группы, типы ошибок (О1–О4), «отдельной страницы не оправдывает»** — как в `20-groups-en.md`.
  Отличия ES от EN описаны там, где выдача их показала; группы ES не перевод EN.

---

## 1. Предварительная группировка (шаг 2)

Исходный материал — ES-блоки `10-task-map.md` и строки `corpus/ahrefs/mx/*.csv`. Шум `taro bebida`, `arcano 8`
и английские строки (`tarot cards`) не группировались (`corpus/ahrefs/README.md`).

| Предварительно | Метка | Чем закончилось после выдачи |
|---|---|---|
| «Tarot gratis» (home) | участок | ES-G01 расклад, ES-G02 три карты, ES-G03 ChatGPT; бренды и колоды — исключены |
| Названия карт в `mx/home.csv` (21 из 38 верхних) | спорное | отнесены к ES-G10 (значение карты): выдача — статьи о карте |
| «Sí o no» | участок | ES-G04 инструмент, ES-G05 одна карта, ES-G06 oráculo |
| «Tarot del amor» | группа | ES-G07 |
| «Significado» / «arcanos mayores» | участок | ES-G08 хаб, ES-G09 старшие арканы |
| Карта × контекст | 5 групп | ES-G10 база, ES-G11 invertida, ES-G12 amor, ES-G13 si o no, ES-G14 sentimientos / consejo |
| «Tiradas» | участок | ES-G15 обзор, ES-G16 cruz celta; «tirada de 3 cartas gratis» — в ES-G02 |
| «Arcano de nacimiento» | группа | ES-G17 |
| «Qué carta soy» | спорное | ES-G18 (смешанная выдача) |
| «Tarot diario» | группа | ES-G19 (без пригодной выдачи) |
| «Horóscopo» | группа | ES-G20 (не подтверждена) |
| «Cómo leer» | группа | ES-G21; `curso de tarot` — исключён |
| «Combinaciones» | — | группа не создана: спроса от 50 нет, снимков нет (`10-task-map.md`, тип 11) |

---

## 2. Таблица пересечений выдачи (MX)

Расчёт — скрипт в рабочей папке (не в репозитории) по всем снимкам MX без пометки `stale_serp`. В таблице — все
пары с общим органическим URL и пары с нулём, на которых держится решение.

| Запрос А | Запрос Б | Общих органических URL | Органических URL в топ-10 (А / Б) |
|---|---|---|---|
| `como saber cual es mi carta del tarot` | `que carta del tarot soy` | 5 | 8 / 9 |
| `tarot gratis 3 cartas` | `tirada de 3 cartas gratis` | 5 | 9 / 9 |
| `arcano de nacimiento` | `como saber cual es mi carta del tarot` | 4 | 8 / 8 |
| `arcanos mayores` | `tarot arcanos` | 4 | 7 / 6 |
| `tarot del amor` | `tarot del amor gratis` | 4 | 8 / 9 |
| `arcano de nacimiento` | `que carta del tarot soy` | 3 | 8 / 9 |
| `cartas del tarot` | `tarot` | 3 | 8 / 8 |
| `la estrella tarot` | `la estrella tarot amor` | 2 | 7 / 8 |
| `la torre invertida tarot` | `la torre tarot` | 2 | 8 / 8 |
| `tarot` | `tarot gratis` | 2 | 8 / 9 |
| `tarot` | `tiradas de tarot` | 2 | 8 / 8 |
| `arcanos mayores` | `cartas del tarot` | 1 | 7 / 8 |
| `cartas del tarot` | `tarot arcanos` | 1 | 8 / 6 |
| `cartas del tarot` | `tiradas de tarot` | 1 | 8 / 8 |
| `oraculo si o no` | `tarot si o no` | 1 | 9 / 9 |
| `tarot` | `tarot si o no` | 1 | 8 / 9 |
| `tarot` | `tirada de 3 cartas gratis` | 1 | 8 / 9 |
| `tarot arcanos` | `tarot del amor gratis` | 1 | 6 / 9 |
| `tarot gratis` | `tirada de 3 cartas gratis` | 1 | 9 / 9 |
| `tarot gratis 3 cartas` | `tarot si o no` | 1 | 9 / 9 |
| `tarot si o no` | `tirada de 3 cartas gratis` | 1 | 9 / 9 |
| `tarot si o no` | `tiradas de tarot` | 1 | 9 / 8 |
| `arcano de nacimiento` | `tarot arcanos` | 0 | 8 / 6 |
| `arcanos mayores` | `la estrella tarot` | 0 | 7 / 7 |
| `cartas del tarot` | `la estrella tarot` | 0 | 8 / 7 |
| `cartas del tarot` | `tarot gratis` | 0 | 8 / 9 |
| `chatgpt tarot` | `tarot` | 0 | 4 / 8 |
| `chatgpt tarot` | `tarot gratis` | 0 | 4 / 9 |
| `como leer el tarot` | `curso de tarot` | 0 | 7 / 8 |
| `cruz celta tarot` | `tirada de 3 cartas gratis` | 0 | 7 / 9 |
| `cruz celta tarot` | `tiradas de tarot` | 0 | 7 / 8 |
| `la estrella tarot` | `la torre tarot` | 0 | 7 / 8 |
| `la estrella tarot` | `los enamorados` | 0 | 7 / 6 |
| `la estrella tarot` | `tarot gratis` | 0 | 7 / 9 |
| `la estrella tarot amor` | `tarot del amor` | 0 | 8 / 8 |
| `oraculo si o no` | `tarot si o no 1 carta` | 0 | 9 / 9 |
| `tarot del amor` | `tarot gratis` | 0 | 8 / 9 |
| `tarot gratis` | `tarot gratis 3 cartas` | 0 | 9 / 9 |
| `tarot gratis` | `tarot libra hoy` | 0 | 9 / 4 |
| `tarot si o no` | `tarot si o no 1 carta` | 0 | 9 / 9 |
| `tirada de 3 cartas gratis` | `tiradas de tarot` | 0 | 9 / 8 |

Все остальные пары снимков MX — 0 общих URL. У `chatgpt tarot` и `tarot libra hoy` часть органических позиций
Ahrefs вернул без URL (3 и 3) — в подсчёт вошли только позиции с URL.

---

## 3. Сводка матрицы карта × контекст (Task 5)

Из `10-task-map.md`, раздел 6, колонки Мексики (`corpus/ahrefs/card-context-mx.csv`, 10.11.2026).

| Контекст | Шаблон ES | MX: карт с данными / медиана / карт ≥50 |
|---|---|---|
| reversed | `<carta> invertida` | 78 / 10 / 21 |
| yes-no | `<carta> si o no` | 78 / 20 / 11 |
| feelings | `<carta> sentimientos` | 21 / 0 / 0 |
| advice | `<carta> consejo` | 17 / 0 / 0 |
| love | `<carta> tarot amor` | 78 / 20 / 16 |

Для `sentimientos` и `consejo` данные есть только по 21 и 17 картам из 78; шаблон ES проверен один на контекст
(кроме вариантов имён в `base` и `love`) — числа MX нижняя граница. Дополнительный расчёт по матрице
(11.11.2026): спрос от 50 в love — 8 старших и 8 младших арканов; в invertida — 8 и 13; в si o no — 1 и 10.

Снимки по контекстам: `la estrella tarot`, `la torre tarot` (база), `la torre invertida tarot`, `la estrella tarot
amor`; `los enamorados`. `la muerte tarot invertida` — пустой (`empty_serp`). По `si o no`, `sentimientos`,
`consejo` снимков нет.

---

## 4. Записи итога по группам

Поля — стр. 609 (состав, задача, условия, основания, снимки и документы, исключённое, нерешённое) плюс `type_id`,
статус, проверка на четыре ошибки и предложение.

### ES-G01 — расклад бесплатно онлайн

- **type_id:** `home`. **Статус:** проверена выдачей (ядро); край `tarot` смешанный.
- **Задача:** эти запросы объединены, потому что человек пытается бесплатно разложить карты онлайн и сразу
  получить ответ.
- **Состав (`mx/home.csv`):** `tarot gratis` (12000), `tarot gratis tirada completa` (1800), `tirada de tarot
  gratis` (1400), `tarot online` (1200), `lectura de tarot` (900); `tiradas de tarot gratis` (150)
  (`mx/spreads.csv`).
- **Справочно по странам:** `tarot gratis` — AR 14000, CO 4500, ES 16000, US-ES 3700; `tarot gratis tirada completa`
  — AR 2600, CO 1000, ES 1600, US-ES 700; `tirada de tarot gratis` — AR 1700, CO 100, ES 1400, US-ES 700.
- **Значимые условия:** `gratis` стоит в большинстве формулировок (ограничение); `tirada completa` — полный расклад
  против короткого.
- **Основание:** органика `tarot gratis` — инструменты и главные страницы сайтов-раскладов: nostra-tarot.com
  (/spread_types/day), tarot.run, tarotap.com/es, приложение (play.google.com), juliantarot.com «intuitive tarot»,
  trustedtarot.com/es/tarot-gratis, mysticnova.app, tarotamigo.com «destino completa», ia.gratis. `tarot` ~
  `tarot gratis` — 2 из 8 / 9 (juliantarot.com, tarot.run).
- **Снимки:** `mx/tarot-gratis.json`, `mx/tarot.json`.
- **Проверка ошибок:** О4 — `tarot` (27000) в группу не включён: органика смешанная (es.wikipedia.org, инструменты
  tarotap draw-cards и nostra yes/no, руководство по значениям darkforesttarotcards.com, youtube, приложение) —
  однословный запрос остаётся в списке неопределённых. О1 — три карты вынесены в ES-G02 (0 общих URL с
  `tarot gratis`).
- **Исключено:** `tarot arcanos` (4500), `tarot los arcanos` (1800) — навигация на losarcanos.com (поз. 1), но см.
  ES-G09; `taro bebida` (3900) — шум; `tarot rider waite` (2000), `tarot de marsella` (1700), `tarot egipcio`
  (1100), `tarot leonora carrington` (900) — колоды (З6, открытый вопрос о второй колоде); `tarot cards` (1100) —
  английская строка.
- **Нерешённое:** `tarot gratis tirada completa`, `tarot online`, `lectura de tarot` — снимков нет, отнесены по
  смыслу.
- **Предложение:** сохранить.

### ES-G02 — расклад на три карты онлайн

- **type_id:** `home` / `spreads` (инструмент). **Статус:** проверена выдачей (два снимка).
- **Задача:** человек пытается бесплатно вытянуть три карты онлайн (прошлое–настоящее–будущее) и получить
  толкование.
- **Состав:** `tarot gratis 3 cartas` (2400) (`mx/home.csv`), `tirada de 3 cartas gratis` (700)
  (`mx/spreads.csv`), `tarot 3 cartas gratis` (60) (`mx/one-card.csv`), `tirada de 3 cartas gratis amor` (40),
  `tirada de 3 cartas` (20) (`mx/spreads.csv`).
- **Справочно по странам:** `tarot gratis 3 cartas` — AR 1500, CO 900, ES 1500, US-ES 1100; `tirada de 3 cartas
  gratis` — AR 1300, CO 350, ES 200, US-ES 250.
- **Основание:** `tarot gratis 3 cartas` ~ `tirada de 3 cartas gratis` — 5 из 9 / 9 (tarotoo.com/es/tarot-3-cartas,
  brujasinescoba.com, tarotia.app, tarotap.com/es/yes-or-no-tarot, tarotamigo.com/tarot/tres-cartas). Органика обоих
  — инструменты на 3 карты (tarotime.net, auracosmus.com, marmaratarot.com, yesnotarot.app, tarot.com любовный на
  3 карты). `tarot gratis 3 cartas` ~ `tarot gratis` — 0: три карты обслуживаются другими документами, чем общий
  «tarot gratis».
- **Ответ на неизвестное «tirada в MX — инструмент?»:** да — `tirada de 3 cartas gratis` и `tarot gratis 3 cartas`
  обслуживаются только инструментами. Но `tiradas de tarot` и `cruz celta tarot` — схемы и документы (ES-G15,
  ES-G16): различие задают `gratis` + число карт, а не слово «tirada». В EN то же правило (`20-groups-en.md`,
  EN-G19): `free <N> card tarot reading` — инструмент, `<N> card tarot spread` — статья. Различие языков в
  другом: в MX самый частотный вход в «расклады» — инструментальный.
- **Снимки:** `mx/tirada-de-3-cartas-gratis.json`, `mx/tarot-gratis-3-cartas.json`.
- **Проверка ошибок:** О3 — у tarotamigo.com (в обоих снимках) заголовок «Tarot Gratis 3 Cartas Españolas» —
  испанская колода (З6); tiradastarotgratis.net — «tarot de Marsella»: часть документов — другие колоды.
  Испанскую колоду (`tirada de 3 cartas españolas gratis` (700)) в группу не берём.
- **Исключено:** `tirada de 3 cartas españolas gratis` (700), `tirada de 3 cartas gitanas gratis` (40) — другие
  колоды (З6).
- **Предложение:** сохранить; «отдельный адрес или формат главной» — TGA.

### ES-G03 — таро через ChatGPT

- **type_id:** `home` (связанный вопрос доверия) / `learn`. **Статус:** проверена выдачей (один снимок, 4 URL).
- **Задача:** человек пытается понять, как получить расклад от ChatGPT и можно ли ему доверять.
- **Состав (`mx/home.csv`):** `chatgpt tarot` (1400).
- **Справочно по странам:** AR 600, CO 700, ES 2300, US-ES 1700.
- **Основание:** органика (снимок 11.11.2026, `update_date` 2026-11-01) — обсуждения и инструкции, не чтецы:
  reddit r/mexico «Que opinan de que ChatGPT te lea el tarot», instagram-пост, chatgpt.com/plugins, glamour.mx
  «Lectura de tarot con ChatGPT: cómo hacerla… qué tan precisa es»; три органические позиции без URL — каталог
  плагинов ChatGPT, плагин «The Astro Scope Tarot Reading», пост в facebook. Блок вопросов: «¿Cómo pedirle el
  tarot a Chatgpt?», «¿Qué tan real es el tarot de Chatgpt?», «¿Cuál es la mejor IA para tarot?», «¿Se puede
  obtener una lectura de tarot gratuita en ChatGPT?». С `tarot` и `tarot gratis` — 0 общих URL.
- **Ответ на вопрос карты задач (промпт для ChatGPT или готовый ИИ-чтец):** по выдаче — прежде всего «как сделать в
  ChatGPT и насколько это реально» (инструкции, мнения, вопрос доверия); готовых ИИ-чтецов в органике нет. Это
  отличие от EN: `tarot ai` (US) обслуживают продукты-чтецы.
- **Снимки:** `mx/chatgpt-tarot.json`.
- **Проверка ошибок:** О4 — 4 URL из 7 органических позиций; вывод по одному снимку. О1 — объединять с ES-G01
  нельзя: другая задача (понять способ и надёжность, а не получить расклад).
- **Предложение:** сохранить; кандидат в раздел доверия рядом с инструментом (как `are tarot cards accurate` в
  EN), отдельной страницы выдача не требует — для TGA.

### ES-G04 — ответ sí o no (инструмент таро)

- **type_id:** `yes-no`. **Статус:** проверена выдачей (ядро).
- **Задача:** человек пытается получить короткий ответ «да» или «нет» картами таро на один вопрос.
- **Состав (`mx/yes-no.csv`):** `tarot si o no` (4000), `tarot si o no gratis` (1300), `si o no tarot` (800),
  `tarot del si o no` (500), `tarot del si o no gratis` (450), `tarot gratis si o no` (400), `tirada de tarot gratis
  si o no` (150), `tarot gratis sí o no` (150), `tarot si o no cartas` (100); с требованием гарантии —
  `tarot sí o no 100 efectivo péndulo` (200), `tarot del si o no gratis y muy certero` (80), `tarot si o no 100%
  efectivo` (80), `tarot si o no fiable` (60), `tarot si o no certero` (60); тема — `tarot si o no del amor` (80),
  `tarot si o no trabajo` (50).
- **Справочно по странам:** `tarot si o no` — AR 7600, CO 1300, ES 16000, US-ES 1900; `tarot si o no gratis` — AR 900,
  CO 350, ES 800, US-ES 40; `si o no tarot` — AR 500, CO 70, ES 400, US-ES 100; `tarot del si o no` — AR 1300,
  CO 300, ES 2100, US-ES 80.
- **Значимые условия:** `certero`, `100% efectivo`, `fiable` — З1 (условие пользователя, не обещание);
  `trabajo` — З3 по деньгам и работе (ответ — размышление, не указание); `péndulo` — другой инструмент.
- **Основание:** органика — инструменты да/нет: losarcanos.com/tarot-si-o-no.php (поз. 1), nostra-tarot.com
  yesno, tarotoo.com, jobcannon.io/es, tarotap.com, tarotamigo.com/tarot/si-o-no, tarotreadingapp.com/es,
  aitarot.pro/es; одна статья-инструкция (uncomo.com «cómo hacer una tirada»).
- **Снимки:** `mx/tarot-si-o-no.json`.
- **Проверка ошибок:** О1 — oráculo и одна карта вынесены (ES-G06, ES-G05). О3 — гарантия и тема сохранены
  условиями.
- **Исключено:** `tarot si o no amigo` (400), `tarot amigo si o no` (150) — бренд tarotamigo (снимок устаревший,
  `stale_serp:2024-03`); `oraculo si o no alicia galvan` (50) — персона; `tarot si o no marsella` (60),
  `tarot si o no 5 cartas marsella` (80) — колода (З6); `tarot si o no bola de cristal` (50) — другой инструмент.
- **Предложение:** сохранить.

### ES-G05 — sí o no одной картой

- **type_id:** `yes-no` (формат) с краем к `one-card`. **Статус:** частично (один снимок, слабый).
- **Задача:** человек пытается получить ответ да/нет, вытянув ровно одну карту.
- **Состав (`mx/yes-no.csv`):** `tarot si o no 1 carta` (350), `tarot si o no 1 carta gratis` (200), `tarot gratis si
  o no 1 carta` (150), `tarot sí o no 1 carta gratis` (150), `tarot si o no gratis 1 carta` (50); `tarot si o no una
  carta` (20) (`mx/one-card.csv`); формат «5 cartas» — `tarot si o no 5 cartas` (70).
- **Справочно по странам:** `tarot si o no 1 carta` — AR 150, CO 1800, ES 200, US-ES 100.
- **Основание:** `tarot si o no 1 carta` ~ `tarot si o no` — 0 общих URL из 9 / 9; ~ `oraculo si o no` — 0. Органика:
  два pinterest-подборки, 7tarot.es (7 карт), tarotify.ai «Sí o No (una carta)», reddit, tarotmarsellagratis.com,
  tarotbalance.com «Respuestas Instantáneas de Una Carta», tarot.eu (6 карт), blogspot «Lista de cartas que
  responden SI/NO». Документы — тоже инструменты да/нет, но другие сайты; 3 из 9 — подборки и обсуждения.
- **Ответ на вопрос карты задач (вход в одну карту в MX через да/нет):** подтверждается тем, что выдача по
  `tarot si o no 1 carta` — инструменты да/нет, а не «карта дня»; самостоятельность от ES-G04 не доказана
  (нулевое пересечение при одном типе документа может быть следствием малого спроса и слабой выдачи;
  `update_date` 2026-10-10).
- **Снимки:** `mx/tarot-si-o-no-1-carta.json`.
- **Проверка ошибок:** О2 — риск «разделено одно и то же»: задача та же, что ES-G04, меняется формат. О4 —
  отдельная группа не означает отдельную страницу.
- **Предложение:** оставить на дополнительную проверку; до неё — уточнение формата внутри ES-G04 (отдельной страницы
  не оправдывает — для TGA).

### ES-G06 — oráculo sí o no

- **type_id:** `yes-no`. **Статус:** проверена выдачей (ядро).
- **Задача:** человек пытается получить мгновенный ответ «да / нет» от «оракула» — не обязательно картами таро.
- **Состав (`mx/yes-no.csv`):** `oraculo si o no` (800), `el oraculo del si o no` (350), `oráculo si o no en línea`
  (350), `oraculo si o no gratis online fiable` (300), `oraculo del si o no` (250), `el oraculo si o no` (200),
  `oraculo si o no ia` (200), `oraculo del si o no gratis` (100), `oraculo si o no 200% veraz y asertivo` (80).
- **Справочно по странам:** `oraculo si o no` — MX 800, AR 2000, CO 150, ES 5500, US-ES 350 (`10-task-map.md`,
  таблица по странам); `el oraculo del si o no` — AR 30, CO 10, ES 250, US-ES 20.
- **Значимые условия:** `fiable`, `veraz` — З1; `ia` — способ.
- **Основание разделения с ES-G04:** `oraculo si o no` ~ `tarot si o no` — 1 общий URL из 9 / 9
  (losarcanos.com/tarot-si-o-no.php). Органика — отдельные «оракулы»: oraculosiono.com (главная, поз. 1),
  soytarot.com/oraculos/si-no, tarotamigo.com/adivinacion/oraculo, eltarotgratis.com.ar/oraculos/si-o-no,
  lilimbo.com, приложение «oraculosiono», yesandnowheel.com/es/oracle (колесо); таро-страницы — только losarcanos
  и mysticnova.app/tarot/si-o-no. На одном домене tarotamigo.com — два документа: `/tarot/si-o-no/` (по `tarot si
  o no`) и `/adivinacion/oraculo/` (по `oraculo si o no`).
- **Ответ на неизвестное «считают ли в MX oráculo и tarot одним»:** по документам — нет: сайты держат oráculo
  отдельным инструментом, чаще без карт (колесо, генератор ответа). Страницы не открывались — механика «оракулов»
  выведена из URL и заголовков.
- **Снимки:** `mx/oraculo-si-o-no.json`.
- **Проверка ошибок:** О1 — объединение с ES-G04 по общему «sí o no» было бы ошибкой «объединено лишнее». О4 —
  в ES (страна) спрос на oráculo выше, чем в MX; вывод о разделении — только для MX.
- **Предложение:** сохранить отдельно; подходит ли наш инструмент таро под задачу «оракула» (другой инструмент,
  близко к З6) — TGA.

### ES-G07 — tarot del amor (инструмент)

- **type_id:** `love`. **Статус:** проверена выдачей (два снимка).
- **Задача:** человек пытается получить расклад о своих отношениях и сразу — ответ.
- **Состав (`mx/love.csv`):** `tarot del amor` (500), `tarot certero gratis futuro inmediato amor` (300),
  `tarot del amor gratis` (250), `tarot gratis de amor` (200), `tarot del amor gratis respuesta inmediata` (200),
  `tarot amor` (150), `tarot amor gratis` (150), `tarot gratis 3 cartas amor` (150), `tarot gratis del amor` (100),
  `tarot gratis tirada completa amor` (100).
- **Справочно по странам:** `tarot del amor` — AR 200, CO 250, ES 500, US-ES 200; `tarot del amor gratis` — AR 200,
  CO 60, ES 600, US-ES 80.
- **Значимые условия:** `certero`, `futuro inmediato`, `respuesta inmediata` — З1, З2; `que siente por mi` — З4;
  `3 cartas` — формат.
- **Основание:** `tarot del amor` ~ `tarot del amor gratis` — 4 из 8 / 9 (nostra-tarot.com love,
  tarotap.com/es/love-tarot, tarotoo.com, trustedtarot.com/es/tarot-del-amor). Одно и то же приложение
  (com.tiradasgratis.tarotdelamor) стоит в обоих снимках с разным параметром языка (`hl=es_MX` и `hl=es`) — по
  правилу нормализации это разные URL; как один документ пересечение было бы 5. Остальное: книга на amazon,
  pinterest, статья tarotnova.app о значениях карт в любви, tiradadetarot.com, losarcanos.com, youtube.
- **Снимки:** `mx/tarot-del-amor.json`, `mx/tarot-del-amor-gratis.json`. `tarot certero gratis futuro inmediato amor`
  — `empty_serp`.
- **Проверка ошибок:** О3 — `tarot amor gratis que siente por mi` (150) держится уточнением с пометкой З4, снимка
  нет. `la estrella tarot amor` ~ `tarot del amor` — 0: значение карты в любви — не этот инструмент (ES-G12).
- **Исключено:** `tarot del amor 3 cartas gitano` (100), `tarot gratis de amor gitano` (70) — другая колода (З6);
  `tarot gratis 3 cartas amor dinero y salud` (80) — включает здоровье (З3): тема допустима только без ответа о
  здоровье, в группу не берём; `pareja 8 numerología` (100) — нумерология, вне границ; `alicia galván tarot gratis
  amor` (40) — персона.
- **Нерешённое:** `100 preguntas para tarot amor` (90) — «что спросить», снимка нет.
- **Предложение:** сохранить.

### ES-G08 — хаб значений карт

- **type_id:** `cards`. **Статус:** проверена выдачей (один снимок ядра).
- **Задача:** человек пытается найти значения карт таро — всей колоды или нужной карты в общем списке.
- **Состав:** `cartas del tarot` (3300), `cartas de tarot` (1600), `cartas del tarot significado` (800),
  `cartas tarot` (800) (`mx/home.csv`), `significado de las cartas del tarot` (700), `significado de las 78
  cartas del tarot de marsella` (500), `cartas del tarot y su significado` (90), `significado de las cartas del
  tarot pdf` (100) (`mx/cards.csv`), `que significa cada carta del tarot` (80) (`mx/questions.csv`).
- **Справочно по странам:** `cartas del tarot` — AR 1600, CO 1000, ES 3300, US-ES 500; `cartas de tarot` — AR 6000,
  CO 450, ES 900, US-ES 200; `significado de las cartas del tarot` — AR 600, CO 250, ES 400, US-ES 150.
- **Основание:** органика `cartas del tarot` — хабы значений 78 карт (lecturas.com «significado de las 78 cartas»,
  thetarotlady.com на испанском, darkforesttarotcards.com «Significado de las 78 cartas»), vogue.mx о старших
  арканах, es.wikipedia.org, инструмент tarotap draw-cards, магазин mercadolibre.com.mx, pinterest.
  `cartas del tarot` ~ `tarot` — 3 из 8 / 8; ~ `tarot gratis` — 0; ~ `la estrella tarot` — 0.
- **Ответ на гипотезу карты задач «в MX по общим стартовым ключам заметнее спрос на значения карт»:**
  подтверждена для `cartas del tarot` (3300): ведут хабы значений, а не инструменты (инструмент — 1 из 8). Для
  `tarot` (27000) — частично (смешанная выдача, ES-G01). Названия отдельных карт в `mx/home.csv` — запросы
  значения карты (ES-G10), а не стартовые запросы расклада: Ahrefs отнёс их к «tarot» по совпадению слов.
- **Снимки:** `mx/cartas-del-tarot.json` (картинки 10, AI Overview).
- **Проверка ошибок:** О1 — у `cartas del tarot` есть покупка колоды (mercadolibre.com.mx, картинки amazon, etsy)
  — доля «купить карты» внутри запроса; отмечена, задача группы не меняется. О3 — `de marsella` (З6) — значения
  другой колоды; держится в группе краем с пометкой до решения владельца о второй колоде.
- **Нерешённое:** `significado de las cartas del tarot` (700) — снимка нет.
- **Предложение:** сохранить.

### ES-G09 — старшие арканы как группа

- **type_id:** `cards`. **Статус:** проверена выдачей.
- **Задача:** человек пытается понять, что такое старшие арканы, сколько их и что значит каждый.
- **Состав (`mx/cards.csv`):** `arcanos mayores` (1800), `arcanos mayores tarot` (450), `cuantos arcanos mayores hay`
  (300), `22 arcanos mayores` (250), `22 arcanos mayores significado` (150), `cartas del tarot arcanos mayores`
  (150), `tarot arcanos mayores` (150), `arcanos mayores significado` (100), `cuántos arcanos mayores hay` (90),
  `los arcanos mayores del tarot` (90); `que es un arcano en el tarot` (100) (`mx/questions.csv`).
- **Справочно по странам:** `arcanos mayores` — AR 1300, CO 500, ES 1200, US-ES 150; `arcanos mayores tarot` —
  AR 150, CO 40, ES 150, US-ES 150; `cuantos arcanos mayores hay` — AR 30, CO 70, ES 200, US-ES 20.
- **Основание разделения с ES-G08:** `arcanos mayores` ~ `cartas del tarot` — 1 общий URL из 7 / 8 (vogue.mx).
  Органика — материалы о 22 арканах как группе: astrolink.com, vogue.mx «Los 22 Arcanos Mayores», tarotnova.app
  (Марсель), universodeletras.unam.mx, es.wikipedia.org «Triunfos», gaia.com, scribd (значения прямые и
  перевёрнутые). С `la estrella tarot` — 0.
- **Ответ на вопрос карты задач (отдельная задача «понять, что такое старшие арканы»):** подтверждена по
  документам; адрес (раздел хаба или отдельная страница) — TGA.
- **`tarot arcanos` (4500):** карта задач исключила его как бренд; выдача показывает смешение — losarcanos.com
  (поз. 1) и arcanos.com (главные страницы) плюс 4 из 6 органических URL, общих с `arcanos mayores`
  (astrolink.com, es.wikipedia.org, gaia.com, vogue.mx). Ошибка О4 в исходном решении: запрос не только
  навигационный. Записан краем ES-G09 с пометкой «бренд + справка», в состав не включён.
- **Снимки:** `mx/arcanos-mayores.json`, `mx/tarot-arcanos.json`.
- **Исключено:** `arcano 8` (2900) — шум (`corpus/ahrefs/README.md`).
- **Предложение:** сохранить.

### ES-G10 — значение одной карты (шаблон «<carta> tarot»)

- **type_id:** `cards`. **Статус:** проверена выдачей на 2 картах.
- **Задача:** человек пытается понять, что значит конкретная карта.
- **Состав:** шаблон по 78 картам; матрица `base` — 78 карт с данными, медиана 550, у 41 карты спрос от 500
  (`10-task-map.md`, раздел 5). Примеры: `la estrella tarot` (2600), `el mago tarot` (2500), `el emperador tarot`
  (2500), `la muerte tarot` (2400), `la torre tarot` (2100), `los enamorados tarot` (2100) (`mx/home.csv`);
  `la estrella tarot significado` (200), `que significa la estrella en el tarot` (150) (`mx/cards.csv`); вопросы
  `que significa el 7 de espadas en el tarot` (200), `que significa el sol en el tarot` (200) (`mx/questions.csv`).
- **Справочно по странам:** `la estrella tarot` — AR 2500, CO 150, ES 900, US-ES 200; `la torre tarot` — AR 1200,
  CO 100, ES 700, US-ES 150; `el mago tarot` — AR 2000, CO 100, ES 1400, US-ES 100.
- **Значимые условия:** варианты имён (El Papa / El Hierofante, Caballero / Caballo, Oros / Pentáculos — колонка
  `name_variant` матрицы); `rider waite` — колода.
- **Основание:** `la estrella tarot` ~ `la torre tarot` — 0 (разные карты — разные документы), шаблон документов
  один: tarotdetiziana.com, darkforesttarotcards.com/es-es, es.wikipedia.org, lecturas.com, deckaura.com/es у обеих.
- **Снимки:** `mx/la-estrella-tarot.json`, `mx/la-torre-tarot.json`.
- **Проверка ошибок:** О4 — `los enamorados` (150) (`mx/card-context.csv`): органика смешана с песней «Los
  enamorados» (spotify, два youtube) — без слова «tarot» имя карты неоднозначно; в неопределённые. С `la estrella
  tarot` — 0.
- **Предложение:** сохранить как шаблонную группу.

### ES-G11 — карта invertida

- **type_id:** `card-context` (reversed). **Статус:** частично (снимок на одной карте; второй пустой).
- **Задача:** карта выпала перевёрнутой, человек пытается понять её значение.
- **Состав:** `la torre invertida tarot` (100) (`mx/cards.csv`), `la estrella tarot invertida` (60), `la muerte
  tarot invertida` (50), `que significa la muerte invertida en el tarot` (30) (`mx/card-context.csv`); матрица
  invertida — 78 / 10 / 21.
- **Основание:** `la torre invertida tarot` ~ `la torre tarot` — 2 из 8 / 8 (tarotdetiziana.com — общая статья;
  darkforesttarotcards.com — общая страница карты с заголовком «Significado de La Torre: Invertida, Amor, Sí o
  No»). Отдельные документы о перевёрнутой: deckaura.com «la-torre-invertido-significado», marifranstarot.com,
  reddit. Шум: lacasaencendida.es и timeout.es — выставка «La torre invertida. El tarot como forma y símbolo»
  (2 из 8).
- **Снимки:** `mx/la-torre-invertida-tarot.json`, `mx/la-torre-tarot.json`. `la muerte tarot invertida` —
  `empty_serp`.
- **Проверка ошибок:** О2 — как в EN-G12: общая страница карты с разделом «invertida» ранжируется; отдельный
  адрес выдачей не требуется. О4 — спрос 100 и ниже, один снимок, четверть органики — шум.
- **Предложение:** сохранить как контекст; при медиане 10 в месяц отдельной страницы группа не оправдывает — для
  TGA (риск объёма ES уже записан в карте задач).

### ES-G12 — карта в любви (шаблон «<carta> tarot amor»)

- **type_id:** `card-context` (love). **Статус:** частично (снимок на одной карте).
- **Задача:** человек спрашивал об отношениях и пытается понять, что значит выпавшая карта в любви.
- **Состав:** `el emperador tarot amor` (100), `rey de espadas tarot amor` (100), `rey de copas tarot amor` (90),
  `la templanza tarot amor` (90), `la estrella tarot amor` (80) (`mx/love.csv`); `la luna tarot amor` (40)
  (`mx/card-context.csv`); `el ermitaño tarot significado amor` (70), `9 de oros tarot en el amor` (60)
  (`mx/love.csv`); матрица love — 78 / 20 / 16.
- **Основание:** `la estrella tarot amor` ~ `la estrella tarot` — 2 из 7 / 8 (darkforesttarotcards.com — общая
  страница «Invertida, Amor y Sí o No»; tarotdetiziana.com). Отдельный документ — deckaura.com «la-estrella-
  significado-amor»; общая страница tarotrossana.com «significado, amor, trabajo»; reddit и quora — о чувствах
  другого (переводы англоязычных обсуждений). С `tarot del amor` — 0.
- **Снимки:** `mx/la-estrella-tarot-amor.json`, `mx/la-estrella-tarot.json`.
- **Проверка ошибок:** О3 — шаблон `<carta> tarot amor` — один из вариантов; встречаются `significado amor`,
  `en el amor` — спрос по шаблону может быть занижен (как в EN-G15), не проверено. О1 — reddit / quora о чувствах
  показывают, что «amor» по карте частично означает «что он чувствует» (З4).
- **Предложение:** сохранить; отдельной страницы на карту выдача не требует (общая страница карты с разделом
  amor ранжируется) — для TGA.

### ES-G13 — карта в вопросе sí o no

- **type_id:** `card-context` (yes-no). **Статус:** не проверена (снимков нет).
- **Задача:** карта выпала в вопросе да/нет, человек пытается узнать её вердикт.
- **Состав (`mx/card-context.csv`):** `el diablo tarot si o no` (40), `7 de oros si o no` (40), `5 de oros si o no`
  (40), `4 de oros si o no` (40), `el ermitaño si o no` (30); `la sacerdotisa tarot si o no` (40),
  `el juicio tarot si o no` (40) (`mx/yes-no.csv`); `tarot arcanos mayores si o no` (50); матрица si o no —
  78 / 20 / 11.
- **Основание:** только смысловое; косвенно — darkforesttarotcards.com (общая страница карты) в заголовке
  обещает «Sí o No» (в снимках `la torre invertida tarot` и `la estrella tarot amor`), а в `tarot si o no 1 carta`
  — блог-список «cartas que responden SI/NO». Отдельных документов «<carta> si o no» в снятой выдаче нет.
- **Проверка ошибок:** О4 — вывод EN-G13 (отдельные документы) на MX не переносится без снимка.
- **Предложение:** оставить на дополнительную проверку; при спросе до 50 отдельной страницы на карту группа не
  оправдывает — для TGA.

### ES-G14 — sentimientos / consejo (кандидат, не подтверждён)

- **type_id:** `card-context` (feelings, advice). **Статус:** не проверена; спрос не подтверждён.
- **Задача (гипотеза из EN):** понять карту как чувства другого (З4) или как совет.
- **Состав:** по шаблонам `<carta> sentimientos`, `<carta> consejo` — данные у 21 и 17 карт из 78, ни у одной
  спрос не достигает 50 (`10-task-map.md`, раздел 6); `los enamorados tarot sentimientos` (0), `el ermitaño
  tarot consejo` (0), `el ermitaño como consejo` (0) (`mx/card-context.csv`).
- **Наблюдение из выдачи:** в `la estrella tarot amor` reddit и quora — «¿qué creen que la estrella pueda
  representar los sentimientos…?», «…cuando se refiere a los sentimientos de alguien hacia ti»: тема чувств
  другого существует, но звучит внутри «amor», а не шаблоном `sentimientos`.
- **Нерешённое:** верны ли шаблоны ES (неизвестное карты задач) — по выдаче не решается; нужна проверка
  формулировок носителем, затем — один запрос Ahrefs по исправленным шаблонам.
- **Предложение:** оставить на дополнительную проверку; до неё группа отдельной страницы не оправдывает.

### ES-G15 — обзор схем раскладов (tiradas)

- **type_id:** `spreads`. **Статус:** частично (один снимок, смешанный).
- **Задача:** человек пытается узнать, какие бывают расклады и как их делать.
- **Состав (`mx/spreads.csv`):** `tiradas de tarot` (300), `tipos de tiradas de tarot` (200), `tiradas de tarot
  explicadas` (100), `tiradas del tarot` (100), `tiradas de tarot pdf` (50), `tiradas de tarot ejemplos` (40),
  `tipos de tiradas de tarot pdf` (30), `esquemas tiradas de tarot` (20), `tiradas de tarot para principiantes`
  (20).
- **Справочно по странам:** `tiradas de tarot` — AR 150, CO 100, ES 200, US-ES 60.
- **Основание:** органика `tiradas de tarot` — схемы и подборки: scribd «TIRADAS TAROT TODAS», tarotnova.app
  «tiradas más utilizadas», tarotrossana.com «guía de tiradas», два pinterest, PDF урока (cursoseducate.com);
  2 инструмента (tarotap draw-cards, nostra yes/no). С `tirada de 3 cartas gratis` — 0, с `cruz celta tarot` — 0.
- **Снимки:** `mx/tiradas-de-tarot.json` (картинки 12).
- **Проверка ошибок:** О3 — `pdf` — заметная доля (scribd, PDF): ждут скачиваемую схему. О1 — инструменты (2 из 8)
  — край к ES-G01.
- **Исключено:** `tirada de 3 cartas españolas gratis` (700) и варианты — другая колода (З6).
- **Предложение:** сохранить.

### ES-G16 — cruz celta

- **type_id:** `spreads`. **Статус:** проверена выдачей (ядро).
- **Задача:** человек пытается разложить «кельтский крест» и понять его позиции.
- **Состав (`mx/spreads.csv`):** `cruz celta tarot` (700), `tarot gratis cruz celta` (80) — край, `tarot cruz celta`
  (60), `tirada cruz celta tarot` (50), `tarot cruz celta tirada completa` (30), `cruz celta tarot significado` (20).
- **Справочно по странам:** `cruz celta tarot` — MX 700, AR 200, CO 150, ES 150, US-ES 40 (`10-task-map.md`).
- **Основание:** органика — документы о схеме: три scribd (PDF «Tirada de La Cruz Celta», «Guía Cruz Celta»),
  paulalustemberg.com «cómo se usa, significado de las posiciones», два pinterest, reddit. Инструментов в топ-10
  нет. С `tiradas de tarot` — 0, с `tirada de 3 cartas gratis` — 0.
- **Снимки:** `mx/cruz-celta-tarot.json` (видео 4, блок вопросов).
- **Проверка ошибок:** О4 — `tarot gratis cruz celta` (80) по смыслу — инструмент; снимка нет.
- **Предложение:** сохранить.

### ES-G17 — arcano de nacimiento

- **type_id:** `birth-card`. **Статус:** проверена выдачей (ядро; `como saber mi arcano de nacimiento` — пустой).
- **Задача:** человек пытается вычислить свой аркан по дате рождения и узнать, что он значит.
- **Состав (`mx/birth-card.csv`):** `arcano de nacimiento` (600), `como saber mi arcano de nacimiento` (300),
  `cual es mi arcano de nacimiento` (200), `arcano personal` (200), `mi arcano de nacimiento` (200), `calcular
  arcano de nacimiento` (100), `como sacar tu arcano de nacimiento` (90), `como sacar el arcano de nacimiento` (80),
  `calculadora de arcano personal` (60); страницы результата — `arcano de nacimiento 5` (60), `arcano de nacimiento
  8` (60), `arcano de nacimiento 11` (60) и далее по числам.
- **Справочно по странам:** `arcano de nacimiento` — AR 400, CO 200, ES 150, US-ES 60; `como saber mi arcano de
  nacimiento` — AR 200, CO 50, ES 40, US-ES 20.
- **Значимые условия:** `como saber`, `como sacar` — метод (У1); `calcular` — инструмент; число — описание уже
  вычисленного аркана.
- **Основание:** органика — калькуляторы (enbuscadelcentro.com, theastroscope.com/es, cursosdetarot.cl,
  tarotap.com/es birth card), mysticnova.app «carta de nacimiento», clarin.com «saber arcano… fecha de
  nacimiento», плюс квиз prismatest.com «who-arcana» и tiktok.
- **Снимки:** `mx/arcano-de-nacimiento.json`. Пустые: `como saber mi arcano de nacimiento`.
- **Проверка ошибок:** О1 — 1 из 8 документов — квиз; см. ES-G18.
- **Исключено:** `arcano 5 matriz del destino` (80), `arcano 8 matriz del destino` (80) и т. п. — другая система;
  `arcano 8` (2900) — шум.
- **Предложение:** сохранить.

### ES-G18 — «qué carta / qué arcano soy» (смешанная)

- **type_id:** `birth-card` и `quiz` — не разделено. **Статус:** проверена выдачей; выдача смешанная.
- **Задача (две конкурирующие):** человек пытается узнать «свою» карту — по дате рождения или пройдя тест.
- **Состав:** `que arcano soy` (150), `que carta del tarot soy` (100), `como saber que arcano soy` (80), `como saber
  que carta del tarot soy` (50), `que carta de tarot soy` (20) (`mx/quiz.csv`); `cual es mi carta del tarot` (70),
  `como saber cual es mi carta del tarot` (50) (`mx/birth-card.csv`).
- **Основание:** `que carta del tarot soy` ~ `como saber cual es mi carta del tarot` — 5 из 9 / 8; ~ `arcano de
  nacimiento` — 3 из 9 / 8 (enbuscadelcentro.com калькулятор, mysticnova.app, clarin.com). Органика `que carta del
  tarot soy`: 5 квизов (vam.ac.uk, jobcannon.io/es test, es.wikihow.com test, deckaura.com/es test, buzzfeed.com/mx),
  3 документа по дате рождения (mysticnova, enbuscadelcentro, clarin), 1 — по знаку зодиака (horoscoponegro.com).
  `como saber cual es mi carta del tarot` — 4 к 4.
- **Ответ на неизвестное «que arcano soy — карта рождения или квиз»:** выдача обслуживает оба объяснения
  примерно поровну; в MX пересечение с картой рождения сильнее, чем в EN (`what tarot card am i` ~ `tarot birth
  card` — 1 общий URL). Единственного объяснения нет. Снимки `que arcano soy` и `como saber que arcano soy` —
  пустые: по главной формулировке решение не проверено.
- **Снимки:** `mx/que-carta-del-tarot-soy.json`, `mx/como-saber-cual-es-mi-carta-del-tarot.json`,
  `mx/arcano-de-nacimiento.json`.
- **Проверка ошибок:** О4 — не присваивать группе одно объяснение. О2 — объединение с ES-G17 вероятно, но тип
  страницы (калькулятор с квизом или квиз с калькулятором) — решение TGA.
- **Исключено:** `uquiz test` (80), `test que osito cariñosito eres` (20), `test que elemento eres avatar` (20) —
  не таро.
- **Предложение:** оставить на дополнительную проверку (повторный снимок `que arcano soy`); до неё — связь с
  ES-G17 и с типом quiz.

### ES-G19 — карта дня / одна карта

- **type_id:** `one-card`. **Статус:** не проверена (пригодных снимков нет).
- **Задача (гипотеза):** человек пытается каждый день или разово вытянуть одну карту.
- **Состав (`mx/one-card.csv`):** `tarot diario` (100), `tarot 1 carta gratis` (90), `tarot una carta` (80), `tarot
  del dia de hoy` (70), `tarot una carta gratis` (60), `tarot diario gratis` (50), `tarot del dia` (50), `carta del
  dia tarot` (40).
- **Снимки:** `tarot diario` — `stale_serp:2024-01`, `tarot una carta` — `stale_serp:2022-01` (для проверки не
  используются); `tarot 1 carta gratis` — `empty_serp`.
- **Наблюдение без доказательной силы:** в устаревшем снимке `tarot diario` (2024-01) рядом с ежедневным таро
  (horoscopo.com, losarcanos.com «arcano del día») стоят товары «diario del tarot» — тетради-дневники
  (amazon.com.mx, mercadolibre, etsy): «diario» значит и «ежедневный», и «дневник». Для продукта с дневником
  раскладов это возможная пересекающаяся задача; проверять свежим снимком.
- **Ответ на неизвестное «есть ли в MX ритуал карты дня»:** не решено. Вход в одну карту в MX — через да/нет
  (ES-G05, снимок подтверждает инструменты да/нет, а не ритуал).
- **Предложение:** оставить на дополнительную проверку (снимок `tarot del dia de hoy`); при спросе до 100 отдельной
  страницы группа не оправдывает — для TGA.

### ES-G20 — таро-гороскоп по знаку

- **type_id:** `horoscope`. **Статус:** проверена выдачей (один снимок): задача таро-гороскопа выдачей не
  подтверждена.
- **Задача (гипотеза):** человек пытается прочитать таро-прогноз для своего знака на сегодня.
- **Состав (`mx/horoscope.csv`):** `tarot libra hoy` (60), `horoscopo tarot` (40), `escorpio tarot hoy` (30),
  `tarot escorpio hoy` (30), `horoscopo y tarot gratis` (20).
- **Основание:** органика `tarot libra hoy` (4 URL из 7 органических позиций) — обычные гороскопы на день:
  lecturas.com/horoscopo/libra, lanacion.com.ar/horoscopo/libra, horoscopo.abc.es, tarotamigo.com/horoscopo/diario/
  libra; таро-документов нет. С `tarot gratis` — 0.
- **Снимки:** `mx/tarot-libra-hoy.json`.
- **Проверка ошибок:** О4 — вывод по одному снимку малого запроса.
- **Исключено:** `horoscopo tauro mhoni vidente` (40), `tarot de nara escorpio` (20) — персоны;
  `horoscopo diario leo 2012 tarot 10` (60) — устаревшая дата.
- **Предложение:** оставить на дополнительную проверку; самостоятельная задача в MX не подтверждена (как в
  карте задач) — риск для TGA.

### ES-G21 — научиться читать таро

- **type_id:** `learn`. **Статус:** проверена выдачей (ядро).
- **Задача:** человек пытается научиться читать карты сам.
- **Состав (`mx/learn.csv`):** `como leer el tarot` (700), `como aprender a leer el tarot` (350), `tarot para
  principiantes` (250), `aprender a leer el tarot` (200), `cómo leer el tarot` (100), `como leer el tarot pdf` (100),
  `tarot para principiantes pdf gratis` (100), `guía de tarot para principiantes pdf` (150), `libro para aprender a
  leer el tarot` (60).
- **Справочно по странам:** `como leer el tarot` — MX 700, AR 70, CO 100, ES 100, US-ES 40 (`10-task-map.md`);
  `como aprender a leer el tarot` — AR 20, CO 80, ES 20, US-ES 50; `tarot para principiantes` — AR 90, CO 20,
  ES 30, US-ES 10.
- **Значимые условия:** `pdf`, `libro`, `guía` — ждут скачиваемый материал.
- **Основание:** органика `como leer el tarot` — руководства (darkforesttarotcards.com/es-es «beginner guide»,
  lanacion.com.ar, juliantarot.com/es-419 guide, vogue.es), книга (amazon.com.mx), reddit, youtube.
  С `curso de tarot` — 0.
- **Снимки:** `mx/como-leer-el-tarot.json`. `guía de tarot para principiantes pdf` — `empty_serp`.
- **Проверка ошибок:** О3 — `pdf` / `libro` сохранены уточнением.
- **Исключено:** `curso de tarot` (200), `curso de tarot gratis` (50), `curso de tarot presencial cdmx` (30) —
  органика `curso de tarot` — продажа курсов (facebook-группы, instagram, udemy.com, mercadolibre.com.mx,
  aprendum.mx, alison.com, amazon, scribd): задача «купить курс», вне продукта; `como leer el tarot con baraja
  española` (40), `como leer el tarot de la santa muerte` (20) — другие колоды (З6); `como protegerse al leer el
  tarot` (30) — З5.
- **Предложение:** сохранить (тип learn — только решение, V3).

---

## 5. Неопределённые запросы

| Запрос (спрос, MX) | Источник | Возможные группы | Почему не решено | Что нужно |
|---|---|---|---|---|
| `tarot` (27000) | `mx/home.csv` | ES-G01 / ES-G08 | Смешанная выдача: wikipedia, инструменты, хаб значений, видео, приложение | Оставить связь с обеими; одно слово задачу не задаёт |
| `que es el tarot` (1300), `tarot que es` (600), `que es el tarot y para que sirve` (500) | `mx/home.csv`, `mx/questions.csv` | ES-G01 (пояснение) / ES-G21 | Снимка нет | Снимок `que es el tarot` |
| `cuantas cartas tiene el tarot` (1000) | `mx/home.csv` | ES-G08 / ES-G09 | Справка о колоде; снимка нет | Решение TGA |
| `tarot de marsella` (1700), `tarot rider waite` (2000) | `mx/home.csv` | вне / ES-G08 | Колода (З6); ждёт решения владельца о второй колоде | Решение владельца |
| `que arcano soy` (150), `como saber que arcano soy` (80) | `mx/quiz.csv` | ES-G17 / ES-G18 | Выдача пустая (`empty_serp`) | Повторный снимок |
| `los enamorados` (150) | `mx/card-context.csv` | ES-G10 / не таро | Органика смешана с песней «Los enamorados» (spotify, youtube) | Использовать формы со словом «tarot» |
| `tarot diario` (100) | `mx/one-card.csv` | ES-G19 / «дневник» | Снимок устаревший (2024-01); «diario» = ежедневный и дневник | Свежий снимок |
| `tarot del amor oraculo` (90) | `mx/love.csv` | ES-G07 / ES-G06 | Снимка нет | — |
| `tarot arcanos` (4500), `tarot los arcanos` (1800) | `mx/home.csv` | бренд / ES-G09 | Выдача: бренд + справка о старших арканах | Не оптимизировать под бренд; связь с ES-G09 |
| `100 preguntas para tarot amor` (90), `que preguntar al tarot` (80) | `mx/love.csv`, `mx/questions.csv` | ES-G07 / связанный вопрос | Снимка нет | — |

---

## 6. Неизвестные из карты задач, назначенные задаче 9

| Неизвестное (`10-task-map.md`) | Решение | Основание |
|---|---|---|
| `que arcano soy` — карта рождения или квиз | Не решено: выдача смешанная, главная формулировка — пустой снимок | ES-G18: 5 квизов и 3 документа по дате рождения в `que carta del tarot soy`; 3 общих URL с `arcano de nacimiento` |
| «Tirada» в MX — инструмент? | Да для `tirada de 3 cartas gratis` / `tarot gratis 3 cartas`; `tiradas de tarot`, `cruz celta` — схемы | ES-G02, ES-G15, ES-G16; 0 общих URL между инструментальными и схемными запросами |
| Считают ли в MX «oráculo» и «tarot» одним | Нет, по документам — разные инструменты | ES-G06: 1 общий URL из 9 / 9; tarotamigo.com держит два разных документа |
| Есть ли в MX ритуал «карта дня» | Не решено: пригодных снимков нет | ES-G19 (устаревшие и пустые снимки) |
| Гипотеза «в MX по общим стартовым ключам заметнее спрос на значения карт» | Подтверждена для `cartas del tarot`; для `tarot` — частично | ES-G08, ES-G10 |
| Отдельная задача «понять старшие арканы» | Подтверждена | ES-G09: 1 общий URL с хабом |
| Верны ли шаблоны ES для `sentimientos`, `consejo` | Выдачей не решается | ES-G14: нужна проверка носителем |
| `chatgpt tarot` — промпт или готовый чтец | Инструкции и обсуждения ChatGPT, вопрос доверия | ES-G03 |

---

## 7. Сколько выдачи не хватило

- One-card MX: три снимка непригодны (два устаревших, один пустой) — ES-G19 смысловая.
- Card × context MX: снимки только по La Torre (invertida) и La Estrella (amor); `si o no`, `sentimientos`,
  `consejo` — без выдачи; `la muerte tarot invertida` — пустой.
- Пустые снимки (7 из Task 6) закрыли проверку `que arcano soy`, `como saber mi arcano de nacimiento`,
  `tarot certero gratis futuro inmediato amor`, `guía de tarot para principiantes pdf`.
- Страницы MX не открывались: механика «оракулов» (ES-G06) и наличие разделов на общих страницах карт (ES-G11,
  ES-G12) выведены из заголовков.
- Снимки других испаноязычных стран не делались — выводы о группах только для MX; для Испании, где `oraculo si o
  no` и `tarot si o no` значительно сильнее, разделение ES-G04 / ES-G06 не проверено.

---

## Спорные группы

Заполняется после второго прогона.
