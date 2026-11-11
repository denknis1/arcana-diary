# Группы по выдаче: Arcana Diary, EN (США)

Версия 1.0, 11.11.2026. Метод — «SEO Монстр 2027», 7.5 (стр. 602–609): предварительная группировка от карты задач
(стр. 602–603), сравнение выдачи в одинаковых условиях, документы, а не домены, органика отдельно от спецблоков
(стр. 604–605), смешанная выдача и уточняющие запросы (стр. 605–607), проверка группировки и четыре типа ошибок
(стр. 607–608), поля записи итога по группе (стр. 609). Формулировки книги в файл не переносились — использованы
её поля и порядок проверки.

## Как читать

- **Спрос:** число в скобках после запроса — Ahrefs Keywords Explorer, страна США, 10.11.2026 (корпус
  `corpus/ahrefs/us/<тип>.csv`, `corpus/ahrefs/card-context-us.csv`; если запрос взят из другого файла, он назван).
  `нет данных` — Ahrefs запрос не вернул; `0` — запрос известен, спрос ниже порога. Объёмы других стран здесь не
  используются.
- **Снимки выдачи:** Ahrefs `serp-overview`, США, топ-10 позиций, без колонки трафика. Снимки Task 6 сняты
  10.11.2026, снимки Task 9 — 11.11.2026 (`corpus/serp/queries.csv`, причина съёмки — колонка `reason`). Файл —
  `corpus/serp/us/<slug>.json`; дата обновления выдачи в Ahrefs — поле `update_date` (все используемые снимки US —
  2026 года).
- **Органика:** позиции, где `'organic' in type`, в пределах позиций 1–10; строки `*_sitelink` не считаются;
  URL сравниваются после снятия `https://`, `www.`, хвостового `/`, якоря `#…` и параметра `?tl=`/`?hl=`.
  Число органических URL в топ-10 обычно 8–9: часть позиций занимают AI Overview, блоки вопросов, картинки.
- **Пересечение** — число одинаковых органических URL (документов). Совпадение доменов отмечается словами отдельно
  и как совпадение не считается. Пересечение — свидетельство для проверки, а не правило «N совпало — одна
  страница» (стр. 605).
- **Просмотр документов:** решения приняты по URL, заголовку и метке `page_type` Ahrefs (метка — предположение
  модели Ahrefs, не факт). Открыты два документа (11.11.2026, WebFetch): страница карты The Star у labyrinthos.co
  и инструмент да/нет у horoscope.com; biddytarot.com и tarot.com вернули проверку бота / 403. Где решение
  держится на непросмотренном документе, это сказано в записи.
- **Статус группы:** «проверена выдачей» — есть снимки по ядру и по краю; «частично» — снимок только по ядру
  или край не снят; «не проверена» — группа смысловая, снимков нет (стр. 608: такую группу нельзя называть
  проверенной по выдаче).
- **Тип ошибки** — по стр. 608: О1 объединено лишнее; О2 разделено одно и то же; О3 пропало уточнение; О4 ложная
  определённость.
- Страницы и адреса здесь не назначаются (стр. 609); «отдельной страницы не оправдывает» — наблюдение для TGA
  (задача 11), не решение об объёме страниц (объём — решение владельца, паспорт).
- Шаблонные группы карта × контекст ведутся на уровне типа страницы (решение владельца): одна группа на
  шаблон, доказательства — снимки по одной карте (The Star) плюс сводка матрицы.

---

## 1. Предварительная группировка (шаг 2)

Исходный материал — формулировки `10-task-map.md` (EN-блоки 12 типов) и строки `corpus/ahrefs/us/*.csv` без
`source_tool=related`. Предложение-проверка «эти запросы объединены, потому что человек пытается…» (стр. 602)
записано в каждой группе ниже. Метка из стр. 603: **участок** (широкая тема, ещё не задание на страницу),
**группа** (вокруг одной задачи), **спорное** (в список неопределённых).

| Предварительно | Метка | Чем закончилось после выдачи |
|---|---|---|
| «Расклад онлайн» (home целиком) | участок | разделён: EN-G01 расклад, EN-G02 ИИ-расклад; `near me`, `psychic` — исключены |
| «Одна карта и карта дня» (one-card целиком) | участок | разделён на EN-G03 и EN-G04 (документы расходятся) |
| «Да / нет» (yes-no целиком) | участок | разделён: EN-G05 инструмент, EN-G06 список карт, EN-G07 схема для своей колоды |
| «Любовный расклад» (love целиком) | участок | разделён: EN-G08 расклад-инструмент, EN-G09 любовные схемы |
| «Значения карт» (cards целиком) | участок | EN-G10 хаб, EN-G11 шаблон «карта» |
| «Карта × контекст» (5 контекстов) | 5 групп | EN-G12…EN-G16, по одной на контекст |
| «Расклады» (spreads целиком) | участок | EN-G17 обзор, EN-G18 кельтский крест, EN-G19 три карты |
| «Карта рождения» | группа | EN-G20; `what is my tarot card` — в спорные |
| «Квиз» | группа | EN-G21; `tarot card questions` — отдельная EN-G26 |
| «Таро-гороскоп» | участок | EN-G22 чтение по знаку, EN-G23 соответствие знак ↔ карта; `yes no tarot horoscope` — в EN-G05 |
| «Сочетания» | группа | EN-G24, края не сошлись (0 общих URL) |
| «Обучение» | группа | EN-G25; `tarot decks for beginners` — исключён |

---

## 2. Таблица пересечений выдачи (US)

Расчёт — скрипт в рабочей папке (не в репозитории) по всем снимкам US, кроме устаревших. В таблице — все пары с
хотя бы одним общим органическим URL и пары с нулём, на которых держится решение о разделении.

| Запрос А | Запрос Б | Общих органических URL | Органических URL в топ-10 (А / Б) |
|---|---|---|---|
| `online tarot reading yes or no` | `yes or no tarot` | 7 | 8 / 9 |
| `free tarot reading` | `tarot reading` | 4 | 9 / 8 |
| `online tarot reading yes or no` | `yes no tarot horoscope` | 4 | 8 / 9 |
| `yes no tarot horoscope` | `yes or no tarot` | 4 | 9 / 9 |
| `daily tarot` | `pull a tarot card` | 3 | 9 / 9 |
| `free 3 card tarot reading` | `free tarot reading` | 3 | 9 / 9 |
| `free 3 card tarot reading` | `tarot reading` | 3 | 9 / 8 |
| `tarot birth card` | `tarot birth card calculator` | 3 | 8 / 9 |
| `tarot birth card calculator` | `what is my tarot card` | 3 | 9 / 8 |
| `tarot card quiz` | `what is my tarot card` | 3 | 9 / 8 |
| `the star reversed` | `the star tarot` | 3 | 8 / 8 |
| `the star tarot` | `the star tarot love` | 3 | 8 / 8 |
| `3 card tarot spread` | `free 3 card tarot reading` | 2 | 8 / 9 |
| `daily tarot` | `free 3 card tarot reading` | 2 | 9 / 9 |
| `daily tarot` | `free tarot reading` | 2 | 9 / 9 |
| `daily tarot` | `one card tarot` | 2 | 9 / 9 |
| `daily tarot` | `tarot reading` | 2 | 9 / 8 |
| `free 3 card tarot reading` | `free tarot card reading love` | 2 | 9 / 8 |
| `free 3 card tarot reading` | `pull a tarot card` | 2 | 9 / 9 |
| `free tarot card reading love` | `love tarot` | 2 | 8 / 8 |
| `free tarot reading` | `tarot ai` | 2 | 9 / 9 |
| `love tarot` | `love tarot spread` | 2 | 8 / 8 |
| `love tarot spread` | `tarot spreads` | 2 | 8 / 8 |
| `one card tarot` | `pull a tarot card` | 2 | 9 / 9 |
| `online tarot reading yes or no` | `yes or no tarot accurate 100 percent` | 2 | 8 / 8 |
| `tarot birth card` | `what is my tarot card` | 2 | 8 / 8 |
| `the star reversed` | `the star tarot love` | 2 | 8 / 8 |
| `yes or no tarot` | `yes or no tarot accurate 100 percent` | 2 | 9 / 8 |
| `3 card tarot spread` | `pull a tarot card` | 1 | 8 / 9 |
| `3 card tarot spread` | `tarot spreads` | 1 | 8 / 8 |
| `daily tarot` | `free tarot card reading love` | 1 | 9 / 8 |
| `free tarot card reading love` | `free tarot reading` | 1 | 8 / 9 |
| `free tarot card reading love` | `love tarot spread` | 1 | 8 / 8 |
| `free tarot card reading love` | `pull a tarot card` | 1 | 8 / 9 |
| `free tarot card reading love` | `tarot ai` | 1 | 8 / 9 |
| `free tarot card reading love` | `tarot reading` | 1 | 8 / 8 |
| `free tarot reading` | `pull a tarot card` | 1 | 9 / 9 |
| `free tarot reading` | `tarot horoscope` | 1 | 9 / 9 |
| `free tarot reading` | `yes no tarot horoscope` | 1 | 9 / 9 |
| `how to read tarot cards` | `learn tarot` | 1 | 8 / 8 |
| `how to read tarot cards` | `tarot reading` | 1 | 8 / 8 |
| `list of tarot card combinations meanings` | `tarot card meanings` | 1 | 8 / 7 |
| `love tarot spread` | `tarot spreads for guidance` | 1 | 8 / 8 |
| `pull a tarot card` | `tarot reading` | 1 | 9 / 8 |
| `pull a tarot card` | `tarot spreads` | 1 | 9 / 8 |
| `tarot birth card` | `what tarot card am i` | 1 | 8 / 9 |
| `tarot card quiz` | `what tarot card am i` | 1 | 9 / 9 |
| `tarot horoscope` | `tarot reading` | 1 | 9 / 8 |
| `tarot spreads` | `tarot spreads for guidance` | 1 | 8 / 8 |
| `the star as feelings` | `the star tarot love` | 1 | 8 / 8 |
| `what is my tarot card` | `what tarot card am i` | 1 | 8 / 9 |
| `yes no tarot horoscope` | `yes or no tarot accurate 100 percent` | 1 | 9 / 8 |
| `3 card tarot spread` | `celtic cross tarot` | 0 | 8 / 8 |
| `celtic cross tarot` | `tarot spreads` | 0 | 8 / 8 |
| `daily tarot` | `tarot horoscope` | 0 | 9 / 9 |
| `death tarot card meaning` | `the star tarot` | 0 | 8 / 8 |
| `free tarot reading` | `one card tarot` | 0 | 9 / 9 |
| `how to read tarot cards` | `tarot decks for beginners` | 0 | 8 / 7 |
| `learn tarot` | `tarot decks for beginners` | 0 | 8 / 7 |
| `libra tarot` | `tarot horoscope` | 0 | 6 / 9 |
| `libra tarot` | `zodiac signs tarot cards` | 0 | 6 / 8 |
| `list of tarot card combinations meanings` | `tarot card combinations` | 0 | 8 / 8 |
| `list of tarot card combinations meanings` | `the sun and the moon tarot` | 0 | 8 / 8 |
| `one card tarot` | `tarot card meanings` | 0 | 9 / 7 |
| `online tarot reading yes or no` | `yes or no tarot list` | 0 | 8 / 8 |
| `tarot ai` | `tarot reading` | 0 | 9 / 8 |
| `tarot birth card` | `tarot card quiz` | 0 | 8 / 9 |
| `tarot birth card calculator` | `tarot card quiz` | 0 | 9 / 9 |
| `tarot card combinations` | `the sun and the moon tarot` | 0 | 8 / 8 |
| `tarot card meanings` | `the moon tarot` | 0 | 7 / 8 |
| `tarot card questions` | `tarot card quiz` | 0 | 7 / 9 |
| `tarot horoscope` | `yes no tarot horoscope` | 0 | 9 / 9 |
| `tarot horoscope` | `zodiac signs tarot cards` | 0 | 9 / 8 |
| `the moon tarot` | `the tower tarot meaning` | 0 | 8 / 8 |
| `the star as feelings` | `the star reversed` | 0 | 8 / 8 |
| `the star as feelings` | `the star tarot` | 0 | 8 / 8 |
| `the star as feelings` | `the star yes or no` | 0 | 8 / 8 |
| `the star reversed` | `the star yes or no` | 0 | 8 / 8 |
| `the star tarot` | `the star yes or no` | 0 | 8 / 8 |
| `the star tarot love` | `the star yes or no` | 0 | 8 / 8 |
| `yes or no tarot` | `yes or no tarot list` | 0 | 9 / 8 |

Все остальные пары снимков US — 0 общих URL.

---

## 3. Сводка матрицы карта × контекст (Task 5)

Из `10-task-map.md`, раздел 6, колонки США (`corpus/ahrefs/card-context-us.csv`, 10.11.2026): лучший объём на
карту по шаблону; медиана — по картам с числовым значением.

| Контекст | Шаблон EN | US: карт с данными / медиана / карт ≥50 |
|---|---|---|
| reversed | `<card> reversed` | 77 / 4100 / 77 |
| yes-no | `<card> yes or no` | 77 / 1000 / 77 |
| feelings | `<card> as feelings` | 77 / 200 / 77 |
| advice | `<card> advice` | 77 / 50 / 44 |
| love | `<card> tarot love` | 77 / 20 / 22 |

Дополнительный расчёт по той же матрице (11.11.2026): в контексте love спрос от 50 есть у 21 старшего аркана и
у 1 младшего; в reversed и yes-no — у 21 старшего и у 56 младших. При этом `9 of swords tarot love meaning`
(1400) (`corpus/ahrefs/us/love.csv`) против `nine of swords tarot love` (10) в матрице: шаблон love для младших
арканов занижает спрос (цифра вместо слова и слово `meaning`) — см. EN-G15.

Снимки по контекстам (одна карта, The Star, плюс снимки Task 6): `the star tarot` (база), `the star reversed`,
`the star yes or no`, `the star as feelings`, `the star tarot love`; `the lovers tarot love`; `death tarot card
meaning` (база Death). Снимок `9 of swords tarot love meaning` Ahrefs вернул пустым (`empty_serp`).

---

## 4. Записи итога по группам

Поля записи — стр. 609: состав и исходные формулировки, общая задача, значимые условия, основания объединения
или разделения, использованные снимки и документы, исключённые запросы с причиной, нерешённые вопросы. Добавлены:
`type_id`, статус проверки, проверка на четыре ошибки, предложение (сохранить / разделить / объединить /
дополнительная проверка — стр. 609).

### EN-G01 — бесплатный расклад онлайн

- **type_id:** `home`. **Статус:** проверена выдачей.
- **Задача:** эти запросы объединены, потому что человек пытается прямо сейчас получить расклад на свой вопрос
  бесплатно и онлайн, без живого чтеца.
- **Состав (`us/home.csv`):** `tarot reading` (38000), `free tarot reading` (20000), `tarot card reading`
  (16000), `free tarot card reading` (7800), `online tarot` (3300), `tarot online` (3200), `tarot reading free`
  (2600), `free online tarot reading` (2500), `online tarot reading` (2500), `tarot cards reading` (2400),
  `tarot reading online` (1400), `online tarot card reading` (1400), `free 3 card tarot reading` (1000),
  `7 card tarot reading free` (1100), `free online tarot` (1000).
- **Значимые условия:** `free` — ограничение (платный вход задачу не решает); число карт (`3 card`, `7 card`) —
  формат результата внутри того же инструмента.
- **Основание:** `tarot reading` ~ `free tarot reading` — 4 общих URL из 8 / 9 (free-tarot-reading.net/free,
  llewellyn.com/tarot_reading.php, evatarot.net, tarot.com); край `free 3 card tarot reading` — 3 общих с обоими
  ядрами, документы — инструменты расклада (tarot.com/readings-reports/tarot-readings/free, astroyogi.com,
  78tarot.cards, evatarot.net, tellmytarot.com). Число карт меняет формат, но не задачу и не тип документа.
- **Снимки:** `us/tarot-reading.json`, `us/free-tarot-reading.json`, `us/free-3-card-tarot-reading.json`. Спецблоки:
  AI Overview во всех трёх, блок вопросов в `tarot reading`.
- **Проверка ошибок:** О1 — у `tarot reading` в органике en.wikipedia.org/wiki/Tarot_card_reading и
  vogue.com (руководство для новичка): часть людей хочет понять, что такое чтение, — это уточнение
  `what is a tarot reading` (3200) держится как связанный вопрос внутри группы, а не как отдельное задание
  (снимка по нему нет). О3 — `free` и число карт сохранены как условия.
- **Исключено:** `tarot reading near me` (3400), `tarot card reading near me` (2900), `psychic reading` (6000) —
  офлайн и живой чтец, вне продукта (`10-task-map.md`, исключения); `tarot reading akurat rekomendasi` (700),
  `learn tarot card reading singapore` (700) — не US-спрос по смыслу.
- **Нерешённое:** `7 card tarot reading free` (1100) — снимка нет; `tarot reading` по выдаче смешанная
  (инструменты + справка), ядро группы держится на `free tarot reading`.
- **Предложение:** сохранить.

### EN-G02 — расклад от ИИ

- **type_id:** `home`. **Статус:** частично (один снимок).
- **Задача:** человек пытается получить расклад именно от ИИ — бесплатно и сразу, часто в формате чата.
- **Состав (`us/home.csv`):** `tarot ai` (5900), `ai tarot reading` (3700), `ai tarot` (3400),
  `ai tarot reading free` (900), `free ai tarot reading` (600), `ask tarot ai` (600), `ai tarot chat` (600),
  `chatgpt tarot reading` (500); `yes no tarot ai` (600) (`us/yes-no.csv`) — край к EN-G05.
- **Значимые условия:** `ai`, `chat`, `ask` — способ чтения (диалог), а не тема.
- **Основание:** `tarot ai` ~ `free tarot reading` — 2 общих URL из 9 / 9 (chatarot.ai/en, tarotap.com/en);
  `tarot ai` ~ `tarot reading` — 0. Остальная органика `tarot ai` — ИИ-продукты: play.google.com (приложение),
  akashicstone.com free-ai-tarot, juliantarot.com, aitarot.pro, aikoo.me, lovelanguages.ai, reddit
  (r/SideProject). Документы — продукты-чтецы, не статьи «что такое ИИ-таро».
- **Снимки:** `us/tarot-ai.json` (AI Overview, sitelinks).
- **Проверка ошибок:** О2 — объединение с EN-G01 не подтверждено (2 из 9); разделение тоже не доказано: оба
  набора — инструменты расклада. О4 — `chatgpt tarot reading` (500) снимка нет; в MX аналог `chatgpt tarot`
  обслуживается обсуждениями и инструкциями (`20-groups-es.md`, ES-G03), для США это не проверено.
- **Исключено:** —.
- **Нерешённое:** ищут ли «ИИ вместо человека» или конкретный продукт (вопрос карты задач) — выдача показывает
  продукты, поэтому ответ «инструмент», но доля брендового спроса неизвестна.
- **Предложение:** сохранить как отдельную группу; задача совпадает с продуктом, поэтому вопрос «главная или
  отдельный адрес» — в TGA. Отдельной страницы выдача сама не требует.

### EN-G03 — вытянуть одну карту сейчас

- **type_id:** `one-card`. **Статус:** проверена выдачей (ядро и край).
- **Задача:** человек пытается вытянуть одну случайную карту на текущий вопрос и прочитать её значение.
- **Состав (`us/one-card.csv`):** `one card tarot` (7000), `tarot one card` (1500), `one card tarot reading`
  (1400), `pull a tarot card` (800), `free one card tarot` (500), `one tarot card reading` (500),
  `pull one tarot card` (450), `one card tarot reading free` (400), `pull a tarot card for me` (350),
  `pull a random tarot card` (300), `one card tarot with reversals` (200).
- **Значимые условия:** `for me`, `random` — карту тянет сервис; `with reversals` — условие механики (перевёрнутые).
- **Основание:** `one card tarot` ~ `pull a tarot card` — 2 общих URL из 9 / 9 (labyrinthos.co/pages/one-card-tarot,
  dailyom.com/tarot/one-card-reading). Органика ядра — инструменты и инструкции одной карты (tarot.com
  one-card, dailytarotdraw.com/card-deck, thatoracleguy.com, micheleknight.com, newagestore.com).
- **Снимки:** `us/one-card-tarot.json`, `us/pull-a-tarot-card.json`.
- **Проверка ошибок:** О1 — у `pull a tarot card` есть randomtarotcard.com и serennu.com (генераторы) и статьи о
  схемах (learntarot.com/less5, suburbanwitchery.com) — край размыт, но задача «получить карту» сохраняется.
  О2 — см. EN-G04.
- **Исключено:** `how many tarot cards are there` (2500) — справка о колоде (в список неопределённых).
- **Нерешённое:** `one card tarot yes/no` (600) и родственные — между EN-G03 и EN-G05, снимка нет.
- **Предложение:** сохранить.

### EN-G04 — карта дня (ежедневный ритуал)

- **type_id:** `one-card`. **Статус:** частично (снимок ядра, край `tarot card of the day` не снят).
- **Задача:** человек пытается каждый день получать «свою карту на сегодня» — повторяющийся ритуал, а не
  разовый ответ.
- **Состав (`us/one-card.csv`):** `daily tarot` (3100), `daily tarot draw` (2600), `tarot card of the day`
  (1800), `daily tarot reading` (700), `free daily tarot reading` (600), `daily tarot card` (500),
  `daily tarot spread` (500), `daily tarot card draw` (400), `free daily tarot` (300); тема поверх ритуала —
  `daily love tarot` (250).
- **Значимые условия:** повтор во времени (`daily`, `of the day`); у `daily tarot spread` (500) — схема, а не
  одна карта.
- **Основание разделения с EN-G03:** `daily tarot` ~ `one card tarot` — 2 общих URL из 9 / 9 (два универсальных
  инструмента одной карты). Остальная органика `daily tarot` — «дневные» документы: dailytarotdraw.com (главная),
  tarot.com/daily-tarot-card, nostra-tarot.com/en/spread_types/day, mytarottoday.com, tellmytarot.com/daily-tarot.
  На одном домене tarot.com — два разных документа: `/daily-tarot-card` (по `daily tarot`) и
  `/readings-reports/tarot-readings/one-card` (по `one card tarot`); то же у dailytarotdraw.com (главная против
  `/card-deck`). Это свидетельство разных документов под две задачи, а не разных доменов.
- **Снимки:** `us/daily-tarot.json`. Страница tarot.com/daily-tarot-card не открыта (403) — содержание
  «ритуала» по ней не подтверждено, вывод держится на URL и заголовках.
- **Проверка ошибок:** О2 — риск «разделено одно и то же»: механика одинаковая (одна карта), различие — в
  повторе. Через `pull a tarot card` цепочка `daily tarot` ~ `pull a tarot card` — 3 общих URL, `pull a tarot card` ~ `one card tarot` — 2
  соединяет обе группы; по стр. 608 цепочку не считаем доказательством объединения.
- **Исключено:** `tarot daily horoscope` (250), `daily tarot horoscope` (150) — тип horoscope (EN-G22).
- **Нерешённое:** снимок `tarot card of the day` (1800) для проверки края; повторить снимок `daily tarot` в
  сопоставимых условиях (стр. 606).
- **Предложение:** сохранить отдельно от EN-G03 до TGA; самостоятельный адрес — вопрос TGA (задача и обещание
  различаются повтором; ответ одной карты одинаков).

### EN-G05 — ответ да / нет (инструмент)

- **type_id:** `yes-no`. **Статус:** проверена выдачей (ядро и три края).
- **Задача:** человек пытается получить короткий ответ «да» или «нет» на один закрытый вопрос.
- **Состав (`us/yes-no.csv`):** `yes or no tarot` (42000), `yes no tarot` (33000), `tarot yes or no` (10000),
  `tarot yes no` (6500), `yes or no tarot accurate 100 percent` (2600), `online tarot reading yes or no` (2000),
  `yes no tarot horoscope` (1600), `tarot card yes or no` (1500), `yes and no tarot` (1400), `yes/no tarot`
  (1300), `tarot reading yes or no` (1000), `yes or no tarot free` (900), `accurate yes or no oracle` (800),
  `free yes or no tarot` (800), `yes no tarot ai` (600), `yes or no tarot horoscope` (600),
  `yes or no tarot live` (500).
- **Значимые условия:** `accurate`, `100 percent` — требование гарантии (З1: сохраняется как условие, не как
  обещание); `free`; `ai`; `live`.
- **Основание:** `yes or no tarot` ~ `online tarot reading yes or no` — 7 из 8 / 9; ~ `yes no tarot horoscope` —
  4 из 9 / 9; ~ `yes or no tarot accurate 100 percent` — 2 из 9 / 8, но вся органика края — те же инструменты
  да/нет (tarotap.com, jobcannon.io, tarotreadingapp.com, yesnotarot.org, dailyom.com, yesnotarot.com): тип
  документа совпадает, различаются сайты.
- **`yes no tarot horoscope` (1600) — решение по minor из ревью Task 8:** снимок 11.11.2026, 9 органических
  URL, из них 8 — инструменты и страницы да/нет: horoscope.com/tarot/tarot-yes-no.aspx (поз. 1), zodiacsign.com/tarot/yes-no,
  astrology.com/tarot/yes-no.html, dailyom.com, astroformer.com, tarot.com yes-no, evatarot.net, nostra-tarot.com;
  девятый — instagram.com/popular/yes-no-tarot-horoscope (подборка постов с литеральной фразой). С `tarot horoscope` — 0
  общих URL. Страница horoscope.com открыта: H1 «Yes or No Tarot», интерактивный выбор карты, связи ответа со
  знаком зодиака нет — «horoscope» в запросе указывает на сайт-источник инструмента (horoscope.com,
  астрологические порталы), а не на гороскоп. Запрос отнесён к EN-G05; навигационная доля (horoscope.com)
  возможна и объёмом не отделяется. То же для `yes or no tarot horoscope` (600) — по аналогии, без снимка.
- **Снимки:** `us/yes-or-no-tarot.json`, `us/online-tarot-reading-yes-or-no.json`,
  `us/yes-or-no-tarot-accurate-100-percent.json`, `us/yes-no-tarot-horoscope.json`. Спецблоки: AI Overview у
  всех четырёх, блок вопросов у `online tarot reading yes or no`.
- **Проверка ошибок:** О1 — список карт да/нет и схема «сделай сам» вынесены (EN-G06, EN-G07). О3 —
  `accurate` и `free` сохранены условиями. О4 — `yes or no oracle` (1100) в группу не включён: не установлено,
  таро ли это (в список неопределённых).
- **Исключено:** `eva tarot yes no` (350) — бренд evatarot.net, навигация.
- **Нерешённое:** `one card tarot yes/no` (600) — граница с EN-G03 без снимка.
- **Предложение:** сохранить.

### EN-G06 — какие карты значат «да», какие «нет» (список)

- **type_id:** `yes-no` (справочный материал к инструменту); связь с `card-context` yes-no (EN-G13).
- **Статус:** проверена выдачей (11.11.2026).
- **Задача:** человек пытается узнать правило: какие из 78 карт считаются «да», «нет», «может быть», —
  чтобы самому прочитать ответ.
- **Состав (`us/yes-no.csv`, `us/quiz.csv`, `us/cards.csv`):** `yes or no tarot list` (1200),
  `yes or no tarot cards list` (500), `yes or no tarot cards` (400); `tarot yes or no cards list` (30)
  (`us/pairs.csv`).
- **Основание разделения:** `yes or no tarot list` ~ `yes or no tarot` — 0 общих URL из 8 / 9;
  ~ `online tarot reading yes or no` — 0. Органика списка — справочные статьи по всем 78 картам:
  tarotelements.com, angelorum.co «Yes/No Meanings All 78», darkforesttarotcards.com «Answers for All 78 Cards»,
  californiapsychics.com, selfgazer.com «All 78 Cards», mysticmag.com, pinterest (шпаргалка), scribd (PDF).
  Инструментов нет.
- **Снимки:** `us/yes-or-no-tarot-list.json` (AI Overview, блок вопросов).
- **Проверка ошибок:** О2 — разделение с EN-G05 подтверждено (разные документы и тип ответа: справка против
  инструмента). В карте задач У1 «какая карта что значит в да/нет» назван необходимым для инструмента: группа
  отдельна по выдаче, но её содержание нужно и инструменту.
- **Предложение:** сохранить отдельной группой. Самостоятельный адрес или раздел инструмента — TGA.

### EN-G07 — расклад да/нет своей колодой (схема)

- **type_id:** `yes-no` / `spreads`. **Статус:** не проверена (снимков нет).
- **Задача:** человек пытается сам сделать расклад да/нет своей колодой — нужна процедура, а не ответ.
- **Состав (`us/yes-no.csv`):** `yes or no tarot spread` (900), `3 card yes or no tarot spread free` (500),
  `how to do yes or no tarot` (400).
- **Значимые условия:** `free` у `3 card yes or no tarot spread free` противоречит «своей колоде» — запрос может
  означать инструмент на три карты.
- **Снимки:** нет. Косвенно: reddit «how to perform a yes/no tarot reading» и psychicsource.com (руководство) в
  органике `yes or no tarot` — часть людей по главному запросу ищет процедуру.
- **Проверка ошибок:** О4 — группа смысловая; называть её проверенной нельзя (стр. 608).
- **Предложение:** оставить на дополнительную проверку (снимок `yes or no tarot spread`).

### EN-G08 — любовный расклад (инструмент)

- **type_id:** `love`. **Статус:** проверена выдачей (два снимка).
- **Задача:** человек пытается получить расклад о своих отношениях онлайн.
- **Состав (`us/love.csv`):** `love tarot` (3600), `love tarot reading` (2100), `free love tarot reading` (2000),
  `free tarot card reading love` (1600), `free love tarot` (800), `free tarot love reading` (700), `tarot love`
  (600), `love tarot card` (600), `free love tarot reading online accurate` (600), `online love tarot reading`
  (400), `free accurate tarot reading for love and marriage` (400).
- **Значимые условия:** `accurate` — З1; `marriage` — ожидание прогноза (З2); `what is he thinking` — чтение
  третьего лица (З4).
- **Основание:** `love tarot` ~ `free tarot card reading love` — 2 общих URL из 8 / 8
  (evatarot.net/love-tarot, labyrinthos.co/pages/free-love-tarot-reading). Органика обоих — инструменты и
  сервисные страницы (solstarot.com/love-readings, horoscope.com tarot-true-love, tarotap.com/en/love-tarot,
  soulyatri.com, deckaura.com, lovelanguages.ai) и главные страницы сайтов-раскладов (free-tarot-reading.net,
  tellmytarot.com, evatarot.net).
- **Снимки:** `us/love-tarot.json`, `us/free-tarot-card-reading-love.json`. Спецблоки у `love tarot`: новости
  (12), видео (10) — заметная доля «любовных прогнозов» от медиа.
- **Проверка ошибок:** О1 — схемы для своей колоды вынесены в EN-G09. О3 — `free love tarot what is he thinking`
  (700) оставлен уточнением с пометкой З4; снимка нет.
- **Исключено:** —.
- **Нерешённое:** У2 «какая у меня ситуация» (одна, в паре, бывший) — выдача подстраниц по ситуациям не
  показала, снимков таких формулировок нет.
- **Предложение:** сохранить.

### EN-G09 — любовные схемы раскладов

- **type_id:** `love` / `spreads`. **Статус:** частично (один снимок ядра).
- **Задача:** человек пытается выбрать схему расклада на отношения для своей колоды.
- **Состав (`us/love.csv`, `us/spreads.csv`):** `love tarot spread` (2200), `tarot love spreads` (700),
  `tarot love spread` (700), `tarot spread for love` (700), `tarot spreads for love` (500), `love spreads tarot`
  (500), `love tarot spreads` (500), `love reading tarot spread` (500), `future love tarot spread` (400),
  `love tarot spread for singles` (150), `tarot spreads for relationships` (150), `does he love me tarot spread`
  (100).
- **Значимые условия:** `future` — З2; `for singles`, `relationships` — ситуация; `does he love me` — З4.
- **Основание:** `love tarot spread` ~ `tarot spreads` — 2 общих из 8 / 8 (labyrinthos.co/pages/tarot-spreads-list,
  writualplanner.com love spreads); ~ `love tarot` — 2 (solstarot.com, evatarot.net — инструменты). Органика:
  5 списков/статей схем (labyrinthos, pagangrimoire.com, writualplanner.com, pinterest, forum.thetarot.guru),
  reddit, 2 инструмента.
- **Снимки:** `us/love-tarot-spread.json`.
- **Проверка ошибок:** О1 — смешанная выдача (схемы + инструменты): группа держится на большинстве документов
  (схемы). Край «расклад онлайн» уходит в EN-G08. О2 — с EN-G17 (обзор схем) 2 общих URL; объединение не
  доказано: тема «любовь» меняет набор схем.
- **Предложение:** сохранить; место (тип love или spreads) — TGA.

### EN-G10 — хаб значений карт (список колоды)

- **type_id:** `cards`. **Статус:** частично (снят только `tarot card meanings`).
- **Задача:** человек пытается найти нужную карту в общем списке или охватить значения всей колоды сразу.
- **Состав (`us/cards.csv`):** `tarot card meanings` (29000), `tarot cards list` (6500), `tarot card meanings
  list` (2600), `list of tarot cards` (1700), `tarot cards meaning list with pictures` (1100),
  `tarot card meanings pdf` (1100), `all tarot cards list` (700), `all tarot card meanings` (600),
  `list of all tarot cards` (600), `78 tarot cards list` (600), `tarot card meanings cheat sheet` (400),
  `tarot card meanings major arcana` (250), `rider waite tarot card meanings` (250).
- **Значимые условия:** `pdf`, `cheat sheet`, `with pictures` — формат «всё сразу» (учёба); `rider waite` — колода
  (З6).
- **Основание:** органика `tarot card meanings` — хабы-списки: labyrinthos.co/blogs/tarot-card-meanings-list,
  thetarotlady.com, biddytarot.com/tarot-card-meanings, lunafactory.com, sininlinen.com, reddit, youtube;
  с `the moon tarot` — 0 общих (хаб и страница карты — разные документы).
- **Снимки:** `us/tarot-card-meanings.json`.
- **Проверка ошибок:** О4 — `tarot cards list` (6500) и `list of tarot cards` (1700) отнесены по смыслу; снимка
  нет, они могут обслуживаться другими документами (списки без значений). О3 — `pdf` сохранён уточнением.
- **Исключено:** `tarot card meanings in filipino` (300) — другой язык; `the ultimate guide to tarot card
  meanings` (350) — заголовок чужого документа.
- **Нерешённое:** снимок `tarot cards list`; `how many tarot cards are there` (2500) — в неопределённые.
- **Предложение:** сохранить, край «список» — на дополнительную проверку.

### EN-G11 — значение одной карты (шаблон «<card> tarot»)

- **type_id:** `cards`. **Статус:** проверена выдачей на 4 картах.
- **Задача:** человек пытается понять, что значит конкретная карта (прямое и обычно перевёрнутое положение).
- **Состав:** шаблон по 78 картам, матрица `base` — 77 карт с данными, медиана 1000, у 61 карты спрос от 500
  (`10-task-map.md`, раздел 5). Примеры: `the star tarot` (25000), `the moon tarot` (21000) (`us/cards.csv`),
  `death tarot card meaning` (6600) (`us/card-context.csv`), `the tower tarot meaning` (3700), `three of swords
  meaning` (2400), `the tower tarot card meaning upright and reversed` (2000), `what does the moon tarot card
  mean` (1400), `ix tarot card meaning` (1000).
- **Значимые условия:** `upright and reversed` — оба положения на одной странице; римская цифра — поиск по номеру;
  `rider waite` — колода (З6).
- **Основание:** снимки `the moon tarot`, `the tower tarot meaning`, `death tarot card meaning`, `the star tarot`
  попарно — 0 общих URL (разные карты — разные документы), но шаблон документов один: страница карты на
  labyrinthos.co, biddytarot.com, thetarotguide.com в позициях 2–7 у всех четырёх. Страница The Star у labyrinthos
  открыта: разделы прямого и перевёрнутого значения, любовь, карьера, финансы, «as Feelings», «as Actions» для
  обоих положений; раздела да/нет нет.
- **Снимки:** `us/the-moon-tarot.json`, `us/the-tower-tarot-meaning.json`, `us/death-tarot-card-meaning.json`,
  `us/the-star-tarot.json`.
- **Проверка ошибок:** О3 — у The Star в органике elliotoracle.com/…/the-star-love (поз. 9) — любовный документ
  ранжируется и по базе; отмечено в EN-G15.
- **Исключено:** —.
- **Нерешённое:** римские цифры и числа из `us/birth-card.csv` (`x tarot card meaning` (200), `v tarot card
  meaning` (150), `3 tarot card meaning` (150)) — карта по номеру или карта рождения; в неопределённые.
- **Предложение:** сохранить как шаблонную группу (78 записей одного типа).

### EN-G12 — перевёрнутая карта (шаблон «<card> reversed»)

- **type_id:** `card-context` (reversed). **Статус:** проверена выдачей на одной карте (The Star).
- **Задача:** карта выпала перевёрнутой, человек пытается понять, чем это значение отличается от прямого.
- **Состав (`us/card-context.csv`, матрица):** `the star reversed` (4500), `the star tarot card reversed card
  keywords` (700), `the star reversed meaning` (250), `the star reversed tarot` (150), `the star tarot reversed`
  (150); матрица reversed — 77 / 4100 / 77 (раздел 3).
- **Основание:** `the star reversed` ~ `the star tarot` — 3 общих URL из 8 / 8: общие страницы карты
  labyrinthos.co (поз. 2), biddytarot.com (поз. 3), thetarotguide.com (поз. 7). Отдельные документы о
  перевёрнутой карте тоже есть: teachmetarot.com (урок «reversed», поз. 5), elliotoracle.com/…/the-star-reversed
  (поз. 9), reddit, youtube. Страница labyrinthos содержит раздел «Reversed Star Meaning» (открыта 11.11.2026).
- **Ответ на неизвестное карты задач «ждут ли перевёрнутое значение на странице карты»:** да — лидеры выдачи по
  `the star reversed` — общие страницы карты с разделом перевёрнутого значения; отдельный URL выдачей не
  требуется, но и не исключён (2 отдельных документа в топ-10). Основание — одна карта; по младшим арканам не
  проверено.
- **Снимки:** `us/the-star-reversed.json`, `us/the-star-tarot.json`.
- **Проверка ошибок:** О2 — риск: отдельная группа при общей странице. Группа сохранена как контекст, потому что
  ответ меняется (другое значение) и спрос высокий; решение «раздел или адрес» — TGA. О4 — вывод по одной карте.
- **Предложение:** сохранить; отдельной страницы выдача не оправдывает — это риск для TGA.

### EN-G13 — карта в вопросе да/нет (шаблон «<card> yes or no»)

- **type_id:** `card-context` (yes-no). **Статус:** проверена выдачей на одной карте.
- **Задача:** карта выпала в вопросе да/нет, человек пытается узнать вердикт именно этой карты.
- **Состав:** `the star yes or no` (700) (матрица), `judgement tarot yes or no` (600), `wheel of fortune tarot yes
  or no` (500), `the emperor tarot yes or no` (450), `the moon tarot yes or no` (450) (`us/yes-no.csv`),
  `death card yes or no` (400), `the star reversed yes or no` (400), `death tarot yes or no` (350)
  (`us/card-context.csv`); матрица yes-no — 77 / 1000 / 77.
- **Основание разделения:** `the star yes or no` ~ `the star tarot` — 0 общих URL из 8 / 8; ~ `the star reversed`
  — 0. Органика — документы «карта как да/нет»: sibyltarot.com «Star as Yes or No», selfgazer.com «The Star Yes
  or No», darkforesttarotcards.com «The Star Tarot Meaning, Yes or No», limansa.com «The Star Yes or No»;
  плюс quora, tarotforum.net, reddit; из общих страниц карты — только trustedtarot.com/cards/the-star. Страница
  labyrinthos (лидер базы) раздела да/нет не имеет и в выдаче нет.
- **Снимки:** `us/the-star-yes-or-no.json` (AI Overview, блок вопросов).
- **Проверка ошибок:** О2 — разделение с EN-G11 подтверждено по документам (на одной карте). Связь с EN-G06
  (список): тот же вопрос на уровне колоды.
- **Нерешённое:** проверка на младшем аркане; ограничение — `limansa.com` в заголовке обещает «Pregnancy» (З3:
  у нас такой ответ запрещён).
- **Предложение:** сохранить.

### EN-G14 — карта как чувства другого (шаблон «<card> as feelings»)

- **type_id:** `card-context` (feelings). **Статус:** проверена выдачей на одной карте.
- **Задача:** человек спрашивал о чувствах другого и пытается понять, что значит выпавшая карта в этой роли.
- **Состав (`us/card-context.csv`, матрица):** `the star as feelings` (250), `the empress as feelings` (200),
  `the empress reversed as feelings` (50), `the star reversed as feelings` (50), `the empress as feelings for
  someone` (30); матрица feelings — 77 / 200 / 77.
- **Значимые условия:** З4 — ответ только как гипотеза для размышления, не как факт о другом человеке.
- **Основание разделения:** `the star as feelings` ~ `the star tarot` — 0 из 8 / 8; ~ `the star tarot love` — 1
  (reddit). Органика — профильные документы: angelorum.co «The Star As Feelings», deckaura.com
  «the-star-as-feelings», starandstrength.com, selfgazer.com «What Someone Really Feels», sibyltarot.com; плюс
  reddit, tarotforum.net, quora. Раздел «as Feelings» есть и на общей странице labyrinthos, но она в топ-10 по
  этому запросу не попала.
- **Снимки:** `us/the-star-as-feelings.json` (`update_date` 2026-10-17).
- **Проверка ошибок:** О2 — разделение с EN-G11 подтверждено на одной карте. О3 — условие З4 записано.
- **Предложение:** сохранить.

### EN-G15 — карта в любви (шаблон «<card> tarot love»)

- **type_id:** `card-context` (love). **Статус:** частично (снимок на одной карте; снимок младшего аркана пуст).
- **Задача:** человек спрашивал об отношениях и пытается понять значение выпавшей карты в любовном вопросе.
- **Состав:** `temperance tarot love` (1100), `the world tarot love` (1000), `the emperor tarot love` (1000)
  (`us/love.csv`, совпадают с матрицей), `the star tarot love` (500), `the lovers tarot love` (500),
  `the moon tarot card meaning love` (500) (`us/cards.csv`), `the hierophant tarot meaning love` (600),
  `the devil tarot card meaning in love` (350), `9 of swords tarot love meaning` (1400) (`us/love.csv`).
  Матрица love — 77 / 20 / 22.
- **Основание:** `the star tarot love` ~ `the star tarot` — 3 из 8 / 8 (labyrinthos.co, thetarotguide.com,
  elliotoracle.com/…/the-star-love). Отдельные любовные документы: deckaura.com «The Star Tarot Love Meaning»,
  elliotoracle (ранжируется и по базе), youtube; плюс reddit, tarotforum, quora. Картина как у reversed:
  общая страница карты с разделом «love» (у labyrinthos раздел есть) и отдельные документы рядом.
  `the lovers tarot love` — органика из общих страниц карты The Lovers (labyrinthos, biddytarot, tarotcake и др.):
  имя карты само содержит «love», для проверки шаблона не годится.
- **Неизвестное карты задач «формулировка love для младших арканов»:** по выдаче не решено — снимок
  `9 of swords tarot love meaning` пустой (`empty_serp`). По корпусу решено частично: `9 of swords tarot love
  meaning` (1400) против `nine of swords tarot love` (10) в матрице — для младших арканов шаблон матрицы не
  тот (цифра и `meaning`). Матричное «22 карты ≥50» — нижняя граница. Следующее действие: перезапрос контекста
  love по шаблону `<n> of <suit> tarot love meaning` для 56 младших арканов (Keywords Explorer, задача 10 или
  отдельное решение по бюджету).
- **Снимки:** `us/the-star-tarot-love.json`, `us/the-lovers-tarot-love.json`.
- **Проверка ошибок:** О3 — пропало уточнение в шаблоне матрицы (см. выше). О2 — как в EN-G12: отдельный адрес
  выдачей не требуется.
- **Предложение:** сохранить; объём спроса контекста — пересчитать до TGA.

### EN-G16 — карта как совет (шаблон «<card> advice»)

- **type_id:** `card-context` (advice). **Статус:** не проверена (снимков нет).
- **Задача:** человек пытается понять, что карта советует сделать.
- **Состав (`us/card-context.csv`):** `the star reversed advice` (40), `the hermit advice` (40), `the hermit
  reversed advice` (30), `the hermit as advice` (30); матрица advice — 77 / 50 / 44.
- **Основание:** только смысловое. Косвенно: у labyrinthos на странице карты есть раздел «as Actions» — совет
  может быть частью общей страницы (не проверено выдачей).
- **Проверка ошибок:** О4 — меняет ли контекст ответ, не установлено (как в карте задач).
- **Предложение:** оставить на дополнительную проверку; при спросе 50 в месяц по медиане отдельной страницы
  группа не оправдывает — для TGA.

### EN-G17 — обзор схем раскладов

- **type_id:** `spreads`. **Статус:** проверена выдачей (два снимка).
- **Задача:** человек со своей колодой пытается выбрать схему расклада из многих.
- **Состав (`us/spreads.csv`):** `tarot spreads` (9400), `tarot card spreads` (3200), `tarot spreads for
  guidance` (2700), `different tarot spreads` (700), `beginner tarot spreads` (600), `tarot spreads for
  beginners` (500), `tarot cards spreads` (400), `easy tarot spreads` (350), `tarot reading spreads` (350),
  `simple tarot spreads` (300), `types of tarot spreads` (300); `career tarot spread` (500) — тема, край.
- **Основание:** `tarot spreads` ~ `tarot spreads for guidance` — 1 общий из 8 / 8 (labyrinthos.co/pages/
  tarot-spreads-list). Органика `tarot spreads` — коллекции и списки схем (labyrinthos, emeraldlotusdivination.com,
  suburbanwitchery.com, ethony.com, pinterest, youtube). У `tarot spreads for guidance` — отдельные авторские
  схемы «когда нет ясности» (thetarotlady.com compass spread, incandescenttarot.com, spiritelement.co,
  hermitsmirror.com).
- **Снимки:** `us/tarot-spreads.json`, `us/tarot-spreads-for-guidance.json`.
- **Проверка ошибок:** О1 — `tarot spreads for guidance` по документам ближе к «одна схема на ситуацию», чем к
  обзору; держится в группе как край с пометкой. О3 — уровень (`beginner`, `easy`) сохранён.
- **Исключено:** `tarot cards phasmophobia` (2000) — игра; `are tarot cards real` (1100) — вопрос доверия;
  `tarot cards major arcana` (1800), `how many tarot cards are in a deck` (1100) — справка о колоде (EN-G10 /
  неопределённые).
- **Предложение:** сохранить.

### EN-G18 — кельтский крест

- **type_id:** `spreads`. **Статус:** частично (снимок ядра; край `free tarot reading celtic cross` не снят).
- **Задача:** человек пытается разложить или понять конкретную схему «кельтский крест» и смысл её позиций.
- **Состав (`us/spreads.csv`):** `celtic cross tarot` (5700), `celtic cross tarot spread` (1800), `free tarot
  reading celtic cross` (500), `celtic cross spread tarot` (400), `celtic cross tarot spread positions meaning`
  (300), `tarot celtic cross` (250), `celtic cross tarot reading` (200), `celtic cross tarot spread positions
  meanings` (200).
- **Значимые условия:** `positions meaning` — У1 (необходимый вопрос); `free … reading` — расклад онлайн.
- **Основание:** `celtic cross tarot` ~ `tarot spreads` — 0 из 8 / 8; ~ `3 card tarot spread` — 0. Органика —
  отдельные документы о схеме: biddytarot.com how-to, labyrinthos.co, theirishjewelrycompany.com (позиции),
  reddit, forum; 3 инструмента/расклада онлайн (micheleknight.com free reading, serennu.com, evatarot.net).
- **Снимки:** `us/celtic-cross-tarot.json` (картинки 6, AI Overview).
- **Проверка ошибок:** О1 — смешанная выдача: 5 статей и обсуждений к 3 инструментам; край «расклад онлайн» не проверен.
- **Предложение:** сохранить; разделение «статья / инструмент» — дополнительная проверка (снимок `free tarot
  reading celtic cross`).

### EN-G19 — схема на три карты

- **type_id:** `spreads`. **Статус:** проверена выдачей (ядро и край со стороны инструмента).
- **Задача:** человек со своей колодой пытается выбрать вариант расклада на три карты (прошлое–настоящее–будущее
  и другие).
- **Состав (`us/spreads.csv`):** `3 card tarot spread` (2100), `3 card tarot spreads` (200), `tarot 3 card spread`
  (200), `3 card spread tarot` (200), `three card tarot spreads` (200), `free 3 card tarot spread past, present
  future` (300) — край.
- **Основание разделения со стороны инструмента:** `3 card tarot spread` ~ `free 3 card tarot reading` — 2 из
  8 / 9 (tarot.com free reading, cbdtarot.com online 3-cards). Остальная органика `3 card tarot spread` — статьи и
  списки схем (labyrinthos «18 Simple Tarot Spreads», jesscarlson.com, lunafactory.com, ethony.com, reddit,
  youtube); у `free 3 card tarot reading` — инструменты (EN-G01). Слова `free` + `reading` переводят запрос из
  схемы в инструмент.
- **Ответ на неизвестное «spread в EN — статья?»:** да для `<N> card tarot spread`; `free <N> card tarot
  reading` — инструмент. Различие задаёт модификатор, а не язык (сравнение с MX — `20-groups-es.md`, ES-G02).
- **Снимки:** `us/3-card-tarot-spread.json`, `us/free-3-card-tarot-reading.json`.
- **Проверка ошибок:** О4 — `free 3 card tarot spread past, present future` (300) содержит и `free`, и `spread`;
  снимка нет, отнесён к краю.
- **Предложение:** сохранить; отдельная страница при наличии EN-G17 — вопрос TGA.

### EN-G20 — карта рождения

- **type_id:** `birth-card`. **Статус:** проверена выдачей.
- **Задача:** человек пытается узнать свою карту по дате рождения и что она о нём говорит.
- **Состав (`us/birth-card.csv`):** `tarot birth card` (2500), `birth tarot card` (1400), `tarot birth card
  calculator` (500), `birth tarot card calculator` (300), `what's my tarot card` (200), `tarot birth card
  meaning` (150), `birth card tarot` (150), `my tarot birth card` (150), `what is my birth tarot card` (100),
  `what is my birthday tarot card` (100), `tarot card birthday calculator` (100), `how to find your birth tarot
  card` (60).
- **Значимые условия:** `calculator` — инструмент; `how to find` — метод расчёта (У1).
- **Основание:** `tarot birth card` ~ `tarot birth card calculator` — 3 из 8 / 9 (tarot.com калькулятор,
  tarotschool.com, darkforesttarotcards.com). Органика — калькуляторы и объяснения метода (cassieuhl.com,
  substack «life card», tarotschool.com/BirthCards).
- **Снимки:** `us/tarot-birth-card.json`, `us/tarot-birth-card-calculator.json`.
- **Проверка ошибок:** О1 — с квизом (`tarot card quiz`) 0 общих URL у обоих снимков ядра — смешения нет.
- **Исключено:** `soul card tarot calculator` (30) — соседний расчёт (кандидат в уточнение, не ядро);
  `what is my identifier card tarot` (50) — другой термин (неопределённые).
- **Нерешённое:** `what is my tarot card` (500) — см. раздел 5.
- **Предложение:** сохранить.

### EN-G21 — квиз «какая я карта»

- **type_id:** `quiz`. **Статус:** проверена выдачей (с оговоркой о слабом пересечении).
- **Задача:** человек пытается ради интереса пройти тест и узнать, какая карта его «представляет».
- **Состав (`us/quiz.csv`):** `what tarot card am i` (900), `which tarot card are you` (400), `tarot card quiz`
  (300), `tarot quiz` (200), `what tarot card are you` (200), `tarot card test` (200), `which tarot card represents
  me` (150), `what tarot card am i quiz` (80), `tarot card personality test` (60).
- **Основание:** `tarot card quiz` ~ `what tarot card am i` — 1 из 9 / 9 (quotev.com). Пересечение слабое, но
  тип документа общий: у `tarot card quiz` 8 из 9 — квизы (vam.ac.uk, tarotforthewildsoul.com, buzzfeed,
  wikihow, jobcannon.io, uquiz, familiartarot.com); у `what tarot card am i` — квизы (proprofs, quotev, buzzfeed,
  cocorrina.com) и обсуждения «как узнать свою карту» (straightdope, reddit, quora, forum) плюс одна статья о
  карте рождения (substack). Число совпадений не решает, решает тип документа (стр. 605).
- **Снимки:** `us/tarot-card-quiz.json`, `us/what-tarot-card-am-i.json`.
- **Проверка ошибок:** О4 — `what tarot card am i` частично про карту рождения (1 из 9) и про «как найти свою
  карту» (форумы); отнесён к квизу по большинству. `tarot card meaning quiz` (30) — проверка знаний (учёба),
  исключён из ядра.
- **Исключено:** `which tarot deck is for me quiz` (20) — выбор колоды, вне продукта; `uquiz test` (MX) — не таро.
- **Предложение:** сохранить.

### EN-G22 — таро-прогноз по знаку на период

- **type_id:** `horoscope`. **Статус:** проверена выдачей (два снимка, края расходятся).
- **Задача:** человек пытается прочитать свежий таро-прогноз для своего знака на сегодня или неделю.
- **Состав (`us/horoscope.csv`):** `tarot horoscope` (1100), `horoscope tarot` (1000), `libra tarot` (1300) —
  край, `leo horoscope tarot` (600), `cancer horoscope tarot` (300), `taurus horoscope tarot` (300), `weekly tarot
  horoscope` (250), `tarot daily horoscope` (250), `tarot horoscopes march 31 2026` (250), `free tarot horoscope`
  (200), `daily tarot horoscope` (150).
- **Значимые условия:** дата и период — требование свежести (З2 для формулировок); знак.
- **Основание:** органика `tarot horoscope` — издатели ежедневных прогнозов: tarot.com (главная и /daily-horoscope),
  yourtango.com (раздел и статья на 6 ноября 2026), horoscope.com, metro.co.uk, indiatoday.in. `libra tarot` ~
  `tarot horoscope` — 0 общих URL, но те же домены с документами уровня знака (tarot.com/daily-horoscope/libra,
  yourtango.com …/libra): совпадение доменов, не документов.
- **Снимки:** `us/tarot-horoscope.json`, `us/libra-tarot.json` (новости 12, видео).
- **Проверка ошибок:** О1 — у `libra tarot` 2 из 6 органических — статьи о соответствии знак ↔ карта
  (californiapsychics.com, chhavitarot.com); край смешанный, запрос `libra tarot` держится в группе условно.
  О4 — `yes no tarot horoscope` сюда не относится (EN-G05, 0 общих URL с `tarot horoscope`).
- **Исключено:** `yourtango tarot horoscope` (200), `www tarot com horoscope` (150), `tango tarot horoscope` (150)
  — навигация на бренды; `taurus horoscope elle` (200) — бренд, без таро.
- **Предложение:** сохранить; знаки (12) — шаблон внутри группы.

### EN-G23 — соответствие знак ↔ карта

- **type_id:** `horoscope` (справка) или `cards` — решает TGA. **Статус:** частично (один снимок).
- **Задача:** человек пытается узнать, какая карта таро соответствует его знаку зодиака.
- **Состав (`us/horoscope.csv`):** `zodiac signs tarot cards` (900), `libra tarot card` (600), `zodiac tarot
  cards` (400), `tarot cards and zodiac signs` (300), `astrology tarot cards` (250).
- **Основание разделения:** `zodiac signs tarot cards` ~ `tarot horoscope` — 0 из 8 / 9; ~ `libra tarot` — 0.
  Органика — справочные статьи о соответствиях (tarot.com/astrology/tarot-cards, labyrinthos «astrology and
  tarot correspondences», zodianz.com, stsoleil.com, darkforesttarotcards.com, everybodymind.com, reddit,
  pinterest).
- **Снимки:** `us/zodiac-signs-tarot-cards.json`.
- **Предложение:** сохранить отдельной группой (справка, а не прогноз).

### EN-G24 — сочетания карт (общее)

- **type_id:** `pairs`. **Статус:** частично (два снимка без общих URL).
- **Задача:** человек пытается понять, как читать две-три карты, выпавшие вместе.
- **Состав (`us/pairs.csv`):** `tarot card combinations` (350), `list of tarot card combinations meanings` (100),
  `worst tarot card combinations` (50), `3 card tarot combination meanings` (50), `tarot card combination
  meanings` (40), `3 tarot card combination calculator` (40), `tarot card combinations calculator` (30).
- **Значимые условия:** `calculator` — инструмент на любое сочетание; `3 cards` — сочетание трёх, парой не
  закрывается.
- **Основание:** `tarot card combinations` ~ `list of tarot card combinations meanings` — 0 общих URL из 8 / 8.
  У первого — смешанная выдача (pinterest, astrology.com, youtube, книга redwheelweiser.com, quora,
  llewellyn.com, astratrainer.com); у второго — указатели сочетаний (solstarot.com, learn-tarot-cards.com,
  biddytarot.com guide, mjstarot.com), калькулятор deckaura.com и хаб значений labyrinthos (1 общий URL с
  `tarot card meanings`).
- **Снимки:** `us/tarot-card-combinations.json`, `us/list-of-tarot-card-combinations-meanings.json`.
- **Проверка ошибок:** О1 — края группы не сошлись: «как читать сочетания» (метод) и «указатель значений
  сочетаний» (справка) могут быть разными задачами; при спросе 350 и 100 различие на решение о странице мало
  влияет. О4 — конкретные пары (`the sun and the moon tarot`) — в неопределённые.
- **Предложение:** оставить на дополнительную проверку; по спросу группа отдельной страницы на каждую пару не
  оправдывает (как и в карте задач) — для TGA.

### EN-G25 — научиться читать карты

- **type_id:** `learn`. **Статус:** проверена выдачей (ядро), край `learn tarot` смешанный.
- **Задача:** человек пытается научиться читать карты сам.
- **Состав (`us/learn.csv`):** `how to read tarot cards` (6000), `how to read tarot` (1000), `tarot for beginners`
  (800), `how to read tarot cards for beginners` (600), `tarot cards for beginners` (350), `tarot reading for
  beginners` (350), `how to learn tarot` (200), `learn tarot cards` (200), `learn tarot` (1200) — край;
  `how to read tarot cards for yourself` (80), `how to read tarot cards for someone else` (60).
- **Значимые условия:** `for yourself` / `for someone else` — разные сценарии; `beginners`.
- **Основание:** органика `how to read tarot cards` — руководства для новичка (purenowherearchive.com,
  almanac.com, vogue.com, lightwands.org, the-line-up.com, image.ie, tarot.com/tarot/cards, forum). `learn tarot`
  ~ `how to read tarot cards` — 1 из 8 / 8 (tarot.com/tarot/cards); у `learn tarot` — ресурсы и курсы
  (learntarot.com главная и /cards.htm, подкаст spotify, приложение, youtube, reddit «best way to learn»).
- **Снимки:** `us/how-to-read-tarot-cards.json`, `us/learn-tarot.json`.
- **Проверка ошибок:** О1 — `learn tarot` ищет «где учиться» (курс, ресурс), а не руководство; держится краем.
- **Исключено:** `tarot decks for beginners` (450) и `best tarot decks for beginners` (150) — покупка колоды:
  снимок с товарным блоком (20 товаров), amazon, магазин tarotarts.com; 0 общих URL с обоими снимками группы;
  `how to use terro drain insect killer` (300) — шум; `learn tarot card reading singapore` (700) — локальные
  курсы.
- **Предложение:** сохранить (тип learn — только решение, V3).

### EN-G26 — что спросить у карт

- **type_id:** `home` (связанный вопрос) / `learn`. **Статус:** частично (один снимок).
- **Задача:** человек пытается сформулировать вопрос к раскладу.
- **Состав:** `tarot card questions` (350), `tarot questions to ask` (150) (`us/quiz.csv`), `questions to ask
  tarot cards about love` (300) (`us/love.csv`).
- **Основание:** органика `tarot card questions` — списки вопросов (sherylwagnermedium.com, lightwands.org, gaia.com
  «100 tarot questions», keen.com «75 questions about love», pinterest, reddit, forum); с `tarot card quiz` — 0
  общих URL (Task 6 снимал его как запрос типа quiz; по документам это не квиз).
- **Снимки:** `us/tarot-card-questions.json`.
- **Предложение:** сохранить; отдельной страницы при спросе 350 группа сама не оправдывает — кандидат в раздел
  инструмента (TGA).

---

## 5. Неопределённые запросы

Стр. 603: отдельный список полезнее случайного распределения.

| Запрос (спрос, US) | Источник | Возможные группы | Почему не решено | Что нужно |
|---|---|---|---|---|
| `what is my tarot card` (500) | `us/birth-card.csv` | EN-G20 / EN-G21 | Выдача смешанная: 3 из 8 общих с калькулятором карты рождения (mysticmondays.com, tarot.com, flickerdeck.com), 3 из 8 — с квизом (vam.ac.uk, tarotforthewildsoul.com, buzzfeed) | Оставить связь с обеими группами; решение — TGA (не оптимизировать две страницы под одну фразу, стр. 606) |
| `what is identifier card tarot` (1100) | `us/questions.csv` | EN-G20 / EN-G21 / новое | Термин «identifier/significator» — другая задача; снимка нет | Снимок выдачи |
| `yes or no oracle` (1100), `accurate yes or no oracle` (800) | `us/yes-no.csv` | EN-G05 / вне таро | Не установлено, таро ли «oracle» | Снимок `yes or no oracle` |
| `one card tarot yes/no` (600) | `us/one-card.csv` | EN-G03 / EN-G05 | Снимка нет | Снимок |
| `how many tarot cards are there` (2500), `how many cards in a tarot deck` (4900) | `us/cards.csv`, `us/questions.csv` | EN-G10 / EN-G25 | Справка о колоде; снимок в Task 6 заменён как off-intent | Решение TGA: раздел хаба |
| `x tarot card meaning` (200), `v tarot card meaning` (150), `3 tarot card meaning` (150) | `us/birth-card.csv` | EN-G11 / EN-G20 | Номер карты или результат калькулятора | Снимок одного из запросов |
| `the sun and the moon tarot` (60), `the sun and moon tarot card together meaning` (60) | `us/pairs.csv` | EN-G24 / вне продукта | В органике колода «Sun and Moon Tarot» (tarot.com/tarot/decks/sun-moon, aeclectic.net, benebellwen.com, collective.world) и страницы сочетания (tarostarot.com, mjstarot.com, reddit, forum) — название колоды и пара | Учитывать как пример: имя пары может совпадать с названием колоды |
| `tarot card meanings for each month` (600) | `us/cards.csv` | EN-G10 / EN-G22 | Смысл не установлен | Снимок |
| `free tarot reading by date of birth` (600) | `us/home.csv` | EN-G01 / EN-G20 | Расклад или карта рождения | Снимок |
| `are tarot cards accurate` (600), `how do tarot cards work` (1000) | `us/questions.csv` | вне 12 типов | Вопрос доверия (карта задач: раздел доверия, решает TGA) | — |
| `the lovers tarot love` (500) | `us/card-context.csv` | EN-G15 / EN-G11 | Имя карты содержит «love»; выдача — общие страницы карты | Для шаблона love не использовать |
| `yes or no tarot spread` (900) | `us/yes-no.csv` | EN-G07 / EN-G05 | Снимка нет | Снимок |

---

## 6. Неизвестные из карты задач, назначенные задаче 9

| Неизвестное (`10-task-map.md`) | Решение | Основание |
|---|---|---|
| Одна ли задача у `one card tarot` и `daily tarot` | Разделены: EN-G03 и EN-G04; адрес — TGA | 2 общих URL из 9 / 9; на tarot.com и dailytarotdraw.com — разные документы под «одна карта» и «карта дня» |
| `what is my tarot card` — карта рождения или квиз | Не решено, честно смешанная выдача | 3 из 8 с калькулятором, 3 из 8 с квизом (раздел 5) |
| Ждут ли перевёрнутое значение на странице карты | Да для The Star: лидеры по `the star reversed` — общие страницы карты с разделом reversed; отдельные документы тоже есть | 3 из 8 общих с `the star tarot`; страница labyrinthos открыта. Младшие арканы не проверены; отдельный адрес — TGA |
| Формулировка love для младших арканов | По выдаче не решено (снимок пустой); по корпусу — шаблон матрицы занижает спрос | `9 of swords tarot love meaning` (1400) против `nine of swords tarot love` (10); нужен перезапрос шаблона |
| «Spread» в EN — статья? | Да для `<N> card tarot spread`; с `free` + `reading` — инструмент | 2 общих из 8 / 9 между `3 card tarot spread` и `free 3 card tarot reading`, остальные документы — разных типов |
| `yes no tarot horoscope` (minor ревью Task 8) | EN-G05, инструмент да/нет | 4 общих URL с `yes or no tarot`, 0 — с `tarot horoscope`; страница horoscope.com открыта |

---

## 7. Сколько выдачи не хватило

- Снимки по одной карте (The Star) — для шаблонных групп EN-G12…EN-G15 вывод не переносится автоматически на
  младшие арканы.
- Нет снимков: EN-G07, EN-G16 (группы смысловые); края `tarot card of the day`, `tarot cards list`,
  `free tarot reading celtic cross`, `chatgpt tarot reading`.
- Все снимки — один момент времени (10–11.11.2026); повтор в сопоставимых условиях для пограничных групп EN-G03 /
  EN-G04 и EN-G12 не делался (стр. 606).

---

## Спорные группы

Заполняется после второго прогона.
