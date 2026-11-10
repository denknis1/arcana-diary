# Снимки выдачи (Task 6) — как читать

- Источник: Ahrefs `serp-overview`, `top_positions=10`, страна US или MX, снято 10.11.2026 (`taken_at`); дата
  обновления выдачи в Ahrefs — `update_date` у каждой позиции.
- **Органика:** `type` — список; органический результат — `'organic' in type` (бывает `["organic","video_th"]`).
  Строки `*_sitelink` (`sitelink`, `ai_overview_sitelink`) используют позицию родителя и в подсчёт органики не
  входят. Фильтр `type=` в запросе не убрал `ai_overview_sitelink`: такие строки есть в 34 файлах
  (`note=has_sitelink_rows` в `queries.csv`). На нумерацию органики это не влияет.
- `queries.csv`, колонка `note`:
  - `empty_serp` — Ahrefs вернул пустую выдачу, файла нет (7 запросов MX);
  - `stale_serp:YYYY-MM` — последняя дата выдачи старше 2026 года (3 запроса MX): для проверки групп не
    использовать (c07.05 — сравнимые условия);
  - `has_traffic` — снимок с колонкой `traffic` (только `tarot reading`, US).
- Ручные замены off-intent запросов при отборе (вместо них взят следующий подходящий по смыслу запрос того же
  типа): `how many tarot cards are there`, `yes no tarot horoscope`, `learn tarot card reading singapore`,
  `uquiz test`.
- MX `pairs` — нет запросов со спросом ≥ 50, снимков нет; MX `card-context` — 2 запроса, MX `horoscope` — 1.
- `page_type` — предположение модели Ahrefs, не факт: доли «инструмент / статья» приблизительные.
