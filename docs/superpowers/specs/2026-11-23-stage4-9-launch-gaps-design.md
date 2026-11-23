# Подэтап 4.9: расхождения, найденные текстами этапа 5 — дизайн

Дата: 23.11.2026. Основа: `docs/research/stage5/60-launch-gaps.md` (отчёты авторов служебных страниц и страниц-
инструментов). Решения владельца — формами 23.11.2026 («Да, одним подэтапом»; «Куда ведёт»; «Оставить 7 дней»).

## 1. Что меняется

| № | Изменение | Файлы | Видно посетителю |
|---|---|---|---|
| 1 | **Строка о поставщике ИИ** под полем вопроса на главной, «одной карте», «да или нет», любви (EN/ES): текст `provider_disclosure` из `api/app/safety/texts.{en,es}.json` (перенести в словари сайта). Ссылку на политику добавить, когда страница `/privacy` / `/es/privacidad` опубликована (этап 6), — до того строка без ссылки | `site/src/i18n/{en,es}.ts`, экран вопроса (`NightRoom`/форма инструмента) | да |
| 2 | **Третья позиция — «куда ведёт»** (решение 29): `posPath` EN «Where it's heading», ES «Hacia dónde va». Чтец и промпты не меняются (у них уже «where it leads» / «hacia dónde va»), платный прогон не нужен | `site/src/i18n/{en,es}.ts` | да |
| 3 | **Подпись любовного расклада** `loveLead`: EN «Three cards about you and your relationship: the past, the present and where it's heading.», ES «Tres cartas sobre ti y tu relación: el pasado, el presente y hacia dónde va.» | `site/src/i18n/{en,es}.ts` | да |
| 4 | **Шрифты со своего сервера**: Cormorant Garamond 500/600 и Manrope 400/500/600/700, woff2, латиница + латиница-расширенная (для испанского), лицензия OFL; `@font-face` в стилях, убрать ссылки на fonts.googleapis.com / fonts.gstatic.com из `Base.astro`. Скачивание — только после «да» владельца с источником, версией и размером | `site/public/fonts/`, `site/src/layouts/Base.astro`, стили | нет (вид тот же) |
| 5 | **Сроки хранения**: `events` — удалять строки старше 13 месяцев; лист ожидания Plus — заявки старше 12 месяцев; в `housekeeping.py`. Логи Docker — ротация `max-size: 10m`, `max-file: 3` для всех служб. В логе ошибки удаления аккаунта — без id аккаунта | `api/app/housekeeping.py`, `deploy/docker-compose.yml`, `api/app/routes/account.py` | нет |
| 6 | **`diarySignInSoon`** (показывается, только если вход не настроен на сервере): EN «Signing in isn't available right now.», ES «El acceso no está disponible en este momento.» | `site/src/i18n/{en,es}.ts` | только при сбое настройки |
| 7 | Гость удаляет расклад — **не делаем** (решение 30): расклад гостя сам удаляется через 7 дней, в политике это написано | — | — |

## 2. Тексты этапа 5 после изменения

Страницы-инструменты и служебные страницы, где третья позиция названа «Next step» / «Siguiente paso», —
переписать на «Where it's heading» / «Hacia dónde va» (ветка `stage5-content`). Фразу о Google Fonts в политике
(EN/ES) убрать после п. 4.

## 3. Проверка

- Тесты сайта (`vitest`) и API (`pytest`) зелёные; новые тесты: строка поставщика на четырёх инструментах, подписи
  позиций, очистка `events` и листа ожидания, отсутствие внешних шрифтов в собранном сайте.
- Проверка ветки — Sonnet (решение владельца 23.11: проверки на Sonnet).
- Слияние и выкладка — по слову владельца.
