# Этап 5. План текстов 15 страниц-инструментов и хабов

23.11.2026. Основа: разбор выдачи `40-tools-serp-study.md` (решение 24), карта страниц этапа 1, правила страниц
карт (`30-card-page-rules.md` §3–§6, §9, §14–§15 — безопасность, испанский, решения 16–23 действуют и здесь),
книга: title/description — c03.02 (стр. 189–197), капсула прямого ответа 40–60 слов — c05.06 / c03.06, ИИ-тексты
без выдуманных авторов — c05.06.

## 1. Объём и блоки по страницам

Объём — текст под инструментом или вокруг списка, который видит читатель (без интерфейса инструмента и без списка
карт, который собирается из данных). Цель — медиана топа ± 20 %; где наша сильная сторона (правило да/нет,
честность о точности, «что дальше») — блок сверх медианы.

| Страница | Слов (цель) | Капсула вверху | H2-блоки (по выдаче) |
|---|---|---|---|
| EN `/` | 800–1 000 | нет (инструмент сверху) | How the reading works · How to ask a good question · Which deck and why reversed cards · What a reading can and can't tell you · After the reading (diary, follow-ups) · FAQ |
| EN `/one-card` | 600–800 | нет | When one card is enough · How to read a single card · Upright and reversed · FAQ |
| EN `/daily` | 500–700 | нет | What a card of the day is · How to use it through the day · Same card again? · FAQ |
| EN `/yes-no` | 600–800 | нет | How the yes/no rule works (по нашему правилу) · One card or three · How to ask a yes/no question · What to do with "no" or "not clear yet" · How accurate is it · FAQ |
| EN `/yes-no/cards` | 900–1 200 + список 78 | да | The rule in one paragraph · Cards that lean yes · Cards that lean no · Not clear yet · Reversed cards · FAQ |
| EN `/love` | 1 000–1 300 | нет | What the love spread shows (позиции) · Questions that work in love · Situations (single, together, after a breakup) · What it won't tell you (чувства другого — как значение карт) · FAQ |
| EN `/cards` | 1 000–1 300 + список 78 | да («78 cards: 22 Major, 56 Minor») | What tarot cards are · Major Arcana · Minor Arcana: four suits · Court cards · How to read meanings (upright/reversed) · FAQ |
| EN `/cards/major-arcana` | 1 200–1 500 + список 22 | да («22 cards, 0–XXI») | What the Major Arcana are · The Fool's journey · Strength and Justice numbering (Уэйт) · How they read in a spread · FAQ |
| ES `/es` | 1 200–1 400 | нет | ¿Cómo funciona la lectura? · ¿Cómo hacer una buena pregunta? · ¿Qué baraja usamos? · ¿Qué puede decir el tarot y qué no? · ¿Y si se lo pregunto a ChatGPT? (ES-002) · Preguntas frecuentes |
| ES `/es/carta-del-dia` | 800–1 000 | нет | ¿Qué es la carta del día? · ¿Cómo usarla en tu día? · ¿Y si se repite? · Preguntas frecuentes |
| ES `/es/si-o-no` | 1 000–1 300 | нет | ¿Cómo funciona el sí o no? · ¿Una carta o tres? · ¿Cómo preguntar? · ¿Qué hago con un «no»? · ¿Qué tan certero es? · Preguntas frecuentes |
| ES `/es/amor` | 1 200–1 500 | нет | ¿Qué muestra la tirada del amor? · ¿Qué preguntar? · Situaciones · ¿Qué no te dice? · Preguntas frecuentes |
| ES `/es/tiradas/3-cartas` | 1 000–1 300 | нет | ¿Qué significan las tres posiciones? (pasado–presente–futuro) · ¿Cómo leer las tres juntas? · Ejemplo · Preguntas frecuentes |
| ES `/es/cartas` | 1 300–1 600 + список 78 | да | ¿Qué son las cartas del tarot y cuántas hay? · Arcanos mayores · Arcanos menores y sus palos · Figuras de la corte · ¿Cómo leer los significados? · Preguntas frecuentes |
| ES `/es/cartas/arcanos-mayores` | 1 800–2 200 + список 22 | да | ¿Qué son los arcanos mayores? · ¿Cuántos son y en qué orden? · El viaje del Loco · ¿Cómo se leen en una tirada? · Preguntas frecuentes |

Испанский пишется сам по себе, не переводом; заголовки — вопросы. Блоки «как это работает» описывают **наш**
продукт (чтец, правило да/нет, дневник) — это то, чего нет у топа (разбор, п. 4).

## 2. Интенты (решение 25: ворота «≥ 10 интентов»)

У каждой страницы — поле `intents`: 10+ вопросов из разбора выдачи (как ищут люди, с источником `[PAA]`,
`[Ahrefs]`, `[H2]`, `[карта страниц]`) и для каждого `answered_in` — id блока или вопроса FAQ, где на него есть
прямой ответ. Скрипт проверяет: вопросов ≥ 10, каждый `answered_in` существует, ответ в нём не пустой.

## 3. Метаданные

Title ≤ 60, сущность в первых 35–45 знаках, без бренда (как у карт); description 130–160, факты и следующий шаг.
H1 — см. вопрос владельцу (раздел 6).

## 4. Факты о продукте — из одного места

Лимиты и правила меняются, поэтому в тексте не пишем цифры напрямую, а ставим метки, которые этап 6 подставит из
настроек сервера: `{guest_limit}` (сейчас 2 расклада в день без входа), `{user_limit}` (3 после входа),
`{followups}` (2 бесплатных уточнения), `{diary_free}` (10 последних раскладов в дневнике). Реестр — c08.08.

## 5. Безопасность и источники

Как у карт: без дат, гарантий, «судьбы», здоровья, суда, советов о вложениях; «точность» — честно: таро не
предсказывает будущее, а помогает подумать (без «100 % accurate»). Факты о колоде — из `deck.json` и Уэйта со
страницей; общепринятое (Путь Дурака, масти и стихии **не** называем — решение 10) — как современное чтение.

## 6. Вопрос владельцу

H1 на инструментах сейчас образные («Ask the cards.», «Pregunta a las cartas.»), а ключевой запрос — в мелкой
надписи над ним. Для поиска лучше, чтобы запрос был в H1.

## 7. Файлы и проверка

`content/pages/{en,es}/<page>.json` (схема: title, description, h1, lead, capsule?, blocks[id, heading,
paragraphs], faq[q,a], intents[q, source, answered_in]); проверка `tools/cards/check_tool_pages.py` (объём,
title/description, интенты, словари запретов, метки фактов, совпадения ≤ 3 % между страницами и с картами).
Порядок: 3 автора (opus) по 5 страниц → проверка Sonnet (решение владельца 23.11) → правки → чтение владельцем.
