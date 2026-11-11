# Снимки выдачи (Task 6) — как читать

- Источник: Ahrefs `serp-overview`, `top_positions=10`, страна US или MX, снято 10.11.2026 (`taken_at`); дата
  обновления выдачи в Ahrefs — `update_date` у каждой позиции.
- **Органика:** `type` — список; органический результат — `'organic' in type` (бывает `["organic","video_th"]`).
  Строки `*_sitelink` (`sitelink`, `ai_overview_sitelink`) используют позицию родителя и в подсчёт органики не
  входят. Фильтр `type=` в запросе не убрал `ai_overview_sitelink`: такие строки есть в 34 файлах
  (`note=has_sitelink_rows` в `queries.csv`). На нумерацию органики это не влияет.
- `queries.csv`, колонка `note` (несколько значений через `|`):
  - `empty_serp` — Ahrefs вернул пустую выдачу, файла нет (7 запросов MX);
  - `stale_serp:YYYY-MM` — последняя дата выдачи старше 2026 года (3 запроса MX): для проверки групп не
    использовать (c07.05 — сравнимые условия);
  - `has_traffic` — снимок с колонкой `traffic` (только `tarot reading`, US).
- Ручные замены off-intent запросов при отборе (вместо них взят следующий подходящий по смыслу запрос того же
  типа): `how many tarot cards are there`, `yes no tarot horoscope`, `learn tarot card reading singapore`,
  `uquiz test`.
- MX `pairs` — нет запросов со спросом ≥ 50, снимков нет; MX `card-context` — 2 запроса, MX `horoscope` — 1.
- `page_type` — предположение модели Ahrefs, не факт: доли «инструмент / статья» приблизительные.
- Task 9 (11.11.2026) добавил 15 запросов в `queries.csv` (`reason` начинается с `task 9:`): 14 снимков
  (`taken_at` 2026-11-11, те же параметры — топ-10, без трафика) и 1 пустой (`9 of swords tarot love meaning`,
  US, `empty_serp`). Снимки сняты под конкретные вопросы группировки (`20-groups-en.md`, `20-groups-es.md`);
  2 717 юнитов, строки task `9` в `../ahrefs/ledger.csv`. JSON записан скриптом из ответа инструмента. У
  `chatgpt tarot` (MX) 3 органические позиции и часть строк AI Overview пришли без URL.
