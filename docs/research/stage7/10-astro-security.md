# Этап 7 / 10. Уязвимости Astro 5.18.2: применимость к нашему деплою

Дата исследования: 2026-11-24. Только исследование, в код/lock ничего не менялось.
Источники: `npm audit --json` (docker node:22, без install), GitHub Advisory API (тексты GHSA), `npm view astro time`, grep по `site/src` и `site/astro.config.mjs`.

## 1. Контекст деплоя

- Установлено: `astro 5.18.2` (последняя 5.x, вышла 2026-05-26; новее 5.x нет), `@astrojs/preact 4.1.3`, `vite 6.4.6`, `sharp 0.34.5` (optional dep astro), `esbuild 0.27.7` (+0.25.12 внутри vite), `zod 3.25.76`, `preact 10.29.8`.
- `output: 'static'`, адаптера нет, нет `astro dev`/`astro preview` в проде; `site/dist` раздаёт Caddy (`try_files {path} {path}.html`). Astro-код на сервере в рантайме НЕ исполняется: он работает только внутри `docker run node:22` при сборке (`deploy/build-site.sh`), на входе только наш собственный код и данные (`src/data/*.json`), без пользовательского ввода.
- Эндпоинты `src/pages/sitemap.xml.ts` и `src/pages/data/daily-[lang].json.ts` статичны (генерируются при сборке).
- Единственный сторонний рантайм-код Astro в браузере: скрипт `astro-island` (гидрация 7 островов `client:load/visible`). Он в dist, проверено grep'ом.

Итог `npm audit`: 4 записи (1 critical, 2 high, 1 low), все они «через astro» с fix = `astro@7.4.13` (semver-major). Развёрнуто в 13 GHSA на astro + 3 на sharp + по 1 на zod и esbuild.

## 2. Таблица advisory

Сокращения: «рантайм» = исполняется на сервере/в браузере посетителя при обслуживании сайта; «сборка» = только в контейнере сборки.

### astro

| Advisory | Severity | Что нужно для эксплуатации | Касается нас? | Исправлено в |
|---|---|---|---|---|
| GHSA-26w7-cxv4-gfx2 (RCE через AVIF/libheif в sharp-сервисе) | critical | Astro обрабатывает недоверенный AVIF через image-сервис (`astro:assets`, `<Image>`, `/_image`) | **Нет.** grep `astro:assets\|<Image\|<Picture\|getImage` в `src`: 0 совпадений; нет `.avif/.heic` в `src` и `public` (в public только `cards/back.svg`, шрифты). Картинки не оптимизируются, недоверенных файлов нет. | 7.2.8 (sharp 0.35.4) |
| GHSA-8hv8-536x-4wqp (XSS через имя слота при `client:*`) | high | SSR + имя слота из запроса (`slot={Astro.url.searchParams...}`) | **Нет.** Нет SSR (static), `Astro.url`/`Astro.request` в `src`: 0; `slot=` в `src`: 0. Острова получают только константные props. | 6.3.3 |
| GHSA-2pvr-wf23-7pc7 (SSRF по Host в prerendered error page) | high | SSR + `app.render()` через `createRequestFromNodeRequest` + prerender 404/500 | **Нет.** Нет SSR/адаптера, `prerender` в `src`: 0; 404 отдаёт Caddy (`handle_errors 404 { root * /srv/site ...}`). | 6.4.6 |
| GHSA-4g3v-8h47-v7g6 (reflected XSS в View Transition animation props) | moderate | `ClientRouter`/`transition:animate` с управляемым атакующим `duration` | **Нет.** grep `transition:\|ClientRouter\|ViewTransitions\|astro:transitions`: 0 (в `global.css` только обычный CSS `transition:`). | 7.1.0 (в 6.x не исправлено) |
| GHSA-j687-52p2-xcff (XSS в `define:vars`) | moderate | `<script define:vars={...}>` с недоверенным значением | **Нет.** `define:vars` в `src`: 0. | 6.1.6 |
| GHSA-jrpj-wcv7-9fh9 (XSS через имена атрибутов в spread) | moderate | SSR/сборка, `{...props}` на HTML-элементе, где **ключи** объекта недоверенные | **Нет.** Spread есть только на компонентах (`<CardArt {...props}/>` в `CardFace.tsx` — Preact, не Astro-рендер; `{...f.props}` в тестах), ключи фиксированные, из нашего кода. Нет пользовательского ввода при сборке. | 6.4.6 |
| GHSA-f48w-9m4c-m7f5 (то же, путь `renderHTMLElement`) | moderate | Spread на компонент-подкласс `HTMLElement`, `typeof HTMLElement==='function'` при SSR | **Нет.** Веб-компонентов нет (grep `extends HTMLElement`: 0), SSR нет. | 7.0.6 |
| GHSA-7pw4-f3q4-r2p2 (XSS в `transition:persist/scope` на островах) | low | `transition:*` на `client:*` + недоверенное значение | **Нет.** `transition:` директив 0. | 7.0.4 |
| GHSA-xr5h-phrj-8vxv (replay шифрованных параметров server islands) | low | Server islands (`server:defer`) + динамическая страница | **Нет.** `server:defer`: 0; нет SSR. | 6.1.10 |
| GHSA-376h-93r7-7g6f (обход base-prefix в middleware) | moderate | `base` ≠ `/` + middleware, авторизующий по `context.url.pathname` | **Нет.** `base` не задан, middleware нет (`defineMiddleware\|onRequest`: 0), SSR нет. | 7.2.4 |
| GHSA-98hj-9722-w3j8 (XSS `<script>{value}</script>` в JSX/MDX) | moderate | `.mdx`/`astro:jsx` + недоверенное значение в script/style | **Нет.** `@astrojs/mdx` не подключён, `.mdx` файлов нет. Единственный `set:html` — `JsonLd.astro` (`<script type="application/ld+json" is:inline set:html={ldScript(data)}>`), `ldScript` в `src/lib/jsonld.ts` экранирует `< > &` и U+2028/2029; данные из наших JSON; охраняется тестом `guards.test.ts`. | 7.3.2 |
| GHSA-mh32-jxcr-mh9f (XSS через динамическое имя тега `<Tag/>`) | low | Имя тега из недоверенного ввода | **Нет.** Динамических тегов (`<Tag`, `<Dynamic`, `const X = cond ? 'div'…`) нет. | 7.4.5 |
| GHSA-r3h5-4585-7x3w (чтение файлов через `/_image` в `@astrojs/node`) | moderate | SSR + адаптер `@astrojs/node` + case-sensitive FS + сиблинг `DIST/` | **Нет.** `@astrojs/node` не установлен, SSR нет. | 7.4.7 |

Вывод по astro: 0 из 13 применимы. Все требуют либо SSR/адаптера/сервера (в проде его нет), либо фич, которые мы не используем (image-сервис, view transitions, server islands, middleware, base, MDX, dynamic tags, `define:vars`), либо недоверенного ввода при сборке (его нет, всё из репозитория).

### Транзитивные зависимости

| Advisory | Пакет / версия у нас | Severity | Что нужно | Касается нас? | Исправлено в |
|---|---|---|---|---|---|
| GHSA-f88m-g3jw-g9cj, GHSA-rgj7-g3m4-5g8c, GHSA-wq5f-xc86-pv6w (libvips / libheif / librsvg) | sharp 0.34.5 | high (x3) | Sharp обрабатывает недоверенные изображения (HEIF/AVIF/SVG) | **Нет.** Sharp вызывается только image-сервисом Astro; он не вызывается (нет `astro:assets`). В Caddy sharp не попадает: `dist` статичен. Поверхность атаки нулевая, пока в `src` не появятся оптимизируемые картинки. | sharp 0.35.0 / 0.35.4 / 0.35.5 |
| GHSA-mrhx-c7xc-m3w5 (DoS памяти при валидации массива) | zod 3.25.76 (диапазон `<4.6.6` формально включает 3.x) | high | Приложение валидирует недоверенный большой массив zod-схемой | **Нет.** Zod внутри Astro валидирует только `astro.config`/content-схемы при сборке; в нашем коде zod не импортируется (проверять `grep -rn zod src`: 0), в браузер не попадает. | zod 4.6.6 (astro 7 требует `^4.6.7`) |
| GHSA-g7r4-m6w7-qqqr (arbitrary file read в dev-сервере esbuild, только Windows) | esbuild 0.27.7 | low | Windows + `esbuild --servedir` | **Нет.** Linux, dev-сервер esbuild не запускается. | 0.28.1 |

Vite, preact, @astrojs/preact: advisory в `npm audit` по ним нет (vite 6.4.6, preact 10.29.8, @astrojs/preact 4.1.3 чисты).

## 3. Есть ли исправление внутри 5.x

**Нет.** Последняя 5.x это 5.18.2 (2026-05-26), которая уже стоит. Все 13 advisory исправлены только в 6.x и/или 7.x (минимальные fixed-версии: 6.1.6 / 6.1.10 / 6.3.3 / 6.4.6; а GHSA-4g3v, f48w, 7pw4, 376h, 98hj, mh32, r3h5, 26w7 только в 7.x). Backport-веток 5.x нет, `npm audit fix` без `--force` ничего не даст; `fixAvailable` = только `astro@7.4.13` (major).

Справка по кандидатам (все старше 2 недель на 2026-11-24, правило проекта соблюдено):

| Версия | Дата релиза | Возраст | Заметки |
|---|---|---|---|
| 6.4.8 (последняя 6.x) | 2026-06-17 | ~5 мес. | закрывает часть (6.x-фиксы), НЕ закрывает 7.x-only (4g3v, 26w7, 98hj и др.); unpacked ~2.8 MB; node >=22.12.0; vite ^7.3.2, zod ^4.3.6 |
| 7.4.13 (latest) | 2026-11-18 | 6 дней, **младше 2 недель** | закрывает всё; node >=22.23.4; vite ^8.3.8, zod ^4.6.7; unpacked ~3.0 MB |
| 7.4.12 | 2026-11-13 | 11 дней, младше 2 недель | |
| 7.4.9 / 7.4.10 / 7.4.11 | 2026-11-10 / 11-10 / 11-11 | 13-14 дней | 7.4.10 (11-10) старше 14 дней сегодня или на границе; 7.4.8 (2026-11-09) уже проходит правило |
| 7.4.8 | 2026-11-09 | 15 дней, подходит | первая 7.x, проходящая правило и содержащая все исправления (нужны: r3h5 -> 7.4.7, mh32 -> 7.4.5, остальные ниже). |

Для 7.x закрывающая всё минимальная версия — 7.4.7 (2026-11-05, 19 дней) из-за r3h5; 7.4.8 следующая стабильная. Дополнительно нужен sharp >= 0.35.5 (приходит с astro 7.2.8+ как зависимость; финальную версию подтвердить при установке).

## 4. Рекомендация

**Срочных действий нет (no action now).** Ни одна advisory не применима к статической сборке, раздаваемой Caddy: нет SSR/адаптера/dev-сервера, не используются image-сервис, view transitions, server islands, middleware, base, MDX, динамические теги, `define:vars`; пользовательского ввода при сборке нет. «Critical» в `npm audit` — формальная оценка по диапазону версий, а не реальный риск нашего деплоя.

План на потом (не блокер запуска 2026-12-14):
1. Сейчас: ничего не менять; в `10-astro-security.md` (этот файл) зафиксировать риск как принятый. Не использовать `npm audit fix --force`.
2. Пока остаёмся на 5.18.2, соблюдать «охранные правила», при нарушении которых advisory станут применимыми: не добавлять `astro:assets`/`<Image>` с недоверенными файлами, `@astrojs/node`/SSR, `ClientRouter`/`transition:*`, `server:defer`, middleware, MDX, `define:vars` с динамикой, динамические имена тегов/слотов/ключей spread. Охранный тест можно расширить в `src/lib/guards.test.ts` (уже запрещает `set:html` вне JSON-LD).
3. Апгрейд до 7.x делать отдельной задачей после запуска, не раньше пары недель от релиза выбранной версии (кандидат на момент исследования: 7.4.8, возможно более новая patch к моменту работы), по правилу ≥2 недель. Это major-скачок через 6 и 7: Node >=22.23.4 (образ `node:22` должен быть свежим; проверить `docker pull`), vite 6 -> 8, zod 3 -> 4, возможное обновление `@astrojs/preact` (latest 6.1.6, peer `preact ^10.6.5`) и `@astrojs/check`, vitest-интеграция. Риски: ломающие изменения в конфиге/сборке (`build.format: 'file'`, `trailingSlash: 'never'` — критичны для URL-схемы и Caddy `try_files`), изменения хэширования/имён ассетов, `astro-island` рантайм; потребуются полный `npm run build`, `vitest`, `deploy/test-site-routes.sh` и сравнение `dist` (список файлов, sitemap, canonical, hreflang) до/после. Не делать до запуска — риск регрессии SEO/URL выше, чем риск от неприменимых advisory.
4. Альтернатива «промежуточный» 6.4.8: не рекомендуется (тоже major, двойная миграция, не закрывает 7.x-only advisory).
5. Мониторинг: раз в 2-4 недели `npm audit --json` + сверка с охранными правилами из п. 2; пересмотреть решение, если появится advisory на сборку/статический вывод (например XSS в compiler, затрагивающий обычные `.astro`-шаблоны) либо если добавим SSR.

## 5. Оговорки

- Применимость оценена по коду `site/src` и `astro.config.mjs` на 2026-11-24 и по описаниям GHSA; код сторонних пакетов (`@astrojs/preact`, `@supabase/auth-js`) не аудировался на эти advisory, но они в `npm audit` не фигурируют.
- Для zod: утверждение «наш код не импортирует zod» опирается на отсутствие zod в `package.json` dependencies (есть только транзитивно); отдельный grep по `src` стоит повторить при апгрейде.
- Совместимость 7.x с текущими настройками не проверялась (ничего не устанавливалось).
