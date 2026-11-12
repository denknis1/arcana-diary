# Снимки выдачи (Task 6) — как читать

- Источник: Ahrefs `serp-overview`, `top_positions=10`, страна US или MX, снято 10.11.2026 (`taken_at`); дата
  обновления выдачи в Ahrefs — `update_date` у каждой позиции.
- **Органика:** `type` — список; органический результат — `'organic' in type` (бывает `["organic","video_th"]`).
  Строки `*_sitelink` (`sitelink`, `ai_overview_sitelink`) используют позицию родителя и в подсчёт органики не
  входят. Фильтр `type=` в запросе не убрал `ai_overview_sitelink`: такие строки есть в 34 файлах
  (`note=has_sitelink_rows` в `queries.csv`). На нумерацию органики это не влияет.
- `queries.csv`, колонка `note` (несколько значений через `|`):
  - `empty_serp` — Ahrefs вернул пустую выдачу, файла нет (на 10.11.2026 — 7 запросов MX; с учётом задач 9 и 11b — 11 строк, см. `queries.csv`);
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
- Задача 9, v1.2 (11.11.2026): 8 дополнительных снимков (task `9b` в ledger, 1 204 юнита) — one card против
  карты дня (US), Three of Swords база / reversed / yes-no (US), `tarot del dia de hoy` и Reina de Copas база /
  invertida (MX). Сохранены скриптом из ответов Ahrefs.
- Задача 11b (11.11.2026): 16 запросов Ahrefs `serp-overview` под решения TGA (`40-tga.md` v1.2; `reason`
  начинается с `task 11b:`), 2 362 юнита, строки task `11b` в `../ahrefs/ledger.csv`. Новых файлов — 11; 3 пустые
  выдачи (`empty_serp`); 2 повтора вернули ту же выдачу, что уже лежит в корпусе (`same_serp_as:<файл>`, дубликат
  не создан); `horoscopo tarot` (MX) — `stale_serp:2024-01`. Сохранены скриптом из ответов Ahrefs.
