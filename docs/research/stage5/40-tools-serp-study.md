# Этап 5. Исследование выдачи: инструменты и хабы (15 страниц)

**Дата:** 23.11.2026. **Цель:** понять, что есть на страницах из топ-10 Google по главным запросам 15 страниц-инструментов и хабов Arcana Diary, чтобы тексты под инструментом подбирать по факту. Здесь тексты не пишутся. Метод — как в `10-card-serp-study.md`. Сырые данные — `tools-serp-raw.json`.

---

## Коротко (для владельца)

1. **У инструментов текст короткий, и он не в главной роли.** В США медиана текста на страницах-инструментах ≈ 450–1 200 слов (одна карта ≈ 750, да/нет ≈ 450, любовь ≈ 1 200). Первые места держат почти пустые страницы: horoscope.com и labyrinthos на «да/нет» — 140 и 850 слов. Страницы по 2 500–4 100 слов (deckaura, onecardtarot.online) стоят на 6–9 местах.
2. **В Мексике текста нужно больше, а конкуренция слабее.** Инструменты на испанском: медиана ≈ 1 000–1 450 слов, почти везде есть FAQ (7 из 8 на главной, 6 из 7 на «sí o no»). Домены слабые: пять первых мест по «tarot gratis» — DR 0–52. Мексиканских сайтов в топе нет: в основном Испания и международные ИИ-шаблоны. «Carta del día» — самая лёгкая выдача: нет ни AI Overview, ни «Похожих вопросов», все 10 — инструменты.
3. **Хабы и списки — другое дело.** Страницы «все карты» и «старшие арканы» живут на структуре и списке, текст вокруг ≈ 1 200–1 500 слов (в США) и 1 500–2 500 (в Мексике). Над всеми четырьмя стоят AI Overview и блок «Похожие вопросы» — на «сколько карт в колоде» и «какие 22 арканa» надо отвечать прямо вверху одной фразой.
4. **Что не делает никто:** объяснить, почему получился именно такой ответ (правило да/нет — только у jobcannon и juliantarot), сказать честно, насколько точно чтение, и дать «что делать дальше». Это место нашей страницы.
5. **Лидеры по ссылкам одни и те же:** labyrinthos (DR 67) стоит в 7 из 8 выдач США; tarot.com, dailyom, horoscope.com — следом. Сильных ссылок у молодого сайта не будет, поэтому конкурировать нужно в Мексике и в нишевых хвостах.

**Ahrefs:** израсходовано **2 751 единица** из потолка 3 000 (счётчик ключа 257 131 → 259 882). Остановились до порога 2 800.

**Что не добрано:** (а) вопросы Ahrefs для EN-093, ES-004, ES-099, ES-009 не запрашивались отдельно — интенты там из «Похожих вопросов», заголовков топа и карты страниц; (б) объёмы главных запросов взяты из `page-map-*.csv`, `keywords-explorer-overview` не запускали; (в) у EN-093 только 10 интентов, у EN-006 только 12 (Ahrefs отдаёт нулевую частоту).

---

## 0. Как сделано

- **Выдача:** Ahrefs `serp-overview`, топ-10, США (en) и Мексика (mx). Для каждой страницы взят запрос по задаче страницы с наибольшим объёмом из её списка (в таблицах указан). Результаты вида «AI Overview», «Похожие вопросы», картинки и видео записаны как фичи выдачи; в таблицах только органика.
- **Страницы:** HTML каждой страницы скачан и разобран локально (слова вне меню/подвала, заголовки h1–h4). Слова — приблизительно, ±20%: на страницах со списками карт в счёт входят тексты карт, на страницах с JS-инструментом сервер отдаёт меньше 100 слов (отмечено «<100 (JS)» и в медиану не входит). «Инструмент выше текста» определено по структуре страницы (форма/колода перед первым смысловым H2), не по визуальному рендеру.
- **Не открывали:** форумы, видео, приложения, магазины, соцсети (не статьи). Защита от ботов и ошибки: страницы пропущены, архивные копии, кэши и Scribd не использовались.
- **Интенты:** пометки в скобках — откуда вопрос: `[PAA]` — блок «Похожие вопросы» в выдаче, `[Ahrefs]` — matching-terms (с объёмом), `[H2 …]` — заголовок топ-страницы, `[карта страниц]` — запрос из `page-map-*.csv`.

### Не открыты (с причиной)

| Страница | Где | Причина |
|---|---|---|
| biddytarot.com/tarot-card-meanings | EN-014 #7 | защита от ботов (11 слов) |
| thetarotguide.com/major-arcana | EN-093 #10 | защита от ботов (11 слов) |
| micheleknight.com single-card | EN-005 #4 | ошибка соединения |
| trustedtarot.com/es/tarot-del-amor | ES-009 #1 | защита от ботов |
| tarot-josnell.com | ES-001 #10 | пустой ответ (11 слов) |
| astralgossip.com, marmaratarot.com | ES-004 #6, #10 | ошибка соединения |
| tarotime.net 3 cartas | ES-099 #4 | ошибка соединения |
| lecturas.com 78 cartas | ES-012 #8 | ошибка соединения (403 по прежнему исследованию) |
| tarot.com one-card, dailyom (yes-no, one-card), mytarottoday, tarot.com love 3 cartas, astrolink arcanos-mayores | EN-005/009/001/006, ES-099, ES-091 | открылись, но это JS-инструмент: <100 слов, текст не посчитан |
| reddit, YouTube, Facebook, TikTok, Google Play, MercadoLibre | в разных выдачах | не статьи, только факт присутствия |

---

## EN-001 — Главная (US)

**Главный запрос:** «free tarot reading» (объём в Ahrefs не запрашивался; в карте страниц группа «tarot reading» 38 000). Фичи выдачи: AI Overview (поз.5), видео-миниатюра (поз.7).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | free-tarot-reading.net/free | 40 | инструмент | 1509 | 4/18 |
| 2 | reddit.com/r/TarotReading/comments/1ird80s/free_online_ | 95 | форум | — | — |
| 3 | llewellyn.com/tarot_reading.php | 73 | инструмент | 498 | 1/0 |
| 4 | evatarot.net/ | 37 | инструмент | 514 | 2/1 |
| 6 | dailyom.com/tarot/yes-no | 71 | инструмент | не открыта | — |
| 7 | reddit.com/r/SideProject/comments/1es8zo3/we_made_a_fre | 95 | форум | — | — |
| 8 | tarotap.com/en | 52 | инструмент | 1117 | 2/30 |
| 9 | deckaura.com/pages/free-tarot-reading | 58 | инструмент | 4135 | 7/25 |
| 10 | labyrinthos.co/pages/yes-no-tarot-reading | 67 | инструмент | 854 | 9/6 |

Открыто страниц: 6 из 9 строк; текст посчитан у 6. **Медиана текста: ≈985 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Позиция 5 занята AI Overview, органика — 9 строк. В топе два форумных поста (reddit, DR 95), оба — «мы сделали бесплатный сайт с гаданием».

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 6 из 6 (по структуре страницы, без визуального рендера)
- FAQ: 4 из 6 (llewellyn, tarotap, deckaura, labyrinthos)
- Ссылки на другие расклады (любовь, да/нет, одна карта): 4 из 6
- Отдельное «как это работает / советы к чтению»: 2 из 6 (deckaura — самый длинный, 4 135 слов; free-tarot-reading.net)
- Отдельного блока про точность и ограничения почти нет (только deckaura/llewellyn в виде оговорок)

**Чего никто не делает хорошо:**
- Честный ответ на «насколько это серьёзно / что это за чтение»: большинство молчит или обещает «100% free» без пояснений
- Объяснение, кто читает карты (живой человек, ИИ, случайный выбор) — внятно только у тарот-приложений на ИИ
- Подсказка новичку, что спросить

**Интенты (16):**
1. free tarot reading yes or no (600)
2. free love tarot reading yes or no (300)
3. free tarot card reading yes or no (250)
4. who will i marry tarot free reading (150)
5. ai tarot reading free yes or no (100)
6. free 3 card tarot reading yes or no (90)
7. is he thinking about me tarot reading free (50)
8. free tarot reading what is he thinking (40)
9. how does tarot work (350) [Ahrefs, тема сайта]
10. what are tarot cards (3 400) [Ahrefs, тема]
11. are tarot cards evil (2 300) [Ahrefs, тема]
12. free reading or written reading? [H2 deckaura]
13. how this free online tarot reading works [H2 deckaura]
14. is a free online tarot reading accurate? [H2-типовой у jobcannon/psychicsource]
15. 7 card tarot reading free [запрос из карты страниц]
16. free 3 card tarot reading [запрос из карты страниц]

## EN-005 — Одна карта (US)

**Главный запрос:** «one card tarot» (объём не запрашивался; в карте страниц группа 7 000). Фичи выдачи: AI Overview (поз.3).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | labyrinthos.co/pages/one-card-tarot | 67 | инструмент | 749 | 10/6 |
| 2 | tarot.com/readings-reports/tarot-readings/one-card | 71 | инструмент | <100 (JS) | — |
| 4 | micheleknight.com/free-readings/single-card-tarot-reading/ | 33 | инструмент | не открыта | — |
| 5 | dailyom.com/tarot/one-card-reading | 71 | инструмент | не открыта | — |
| 6 | onecardtarot.online/ | 1 | инструмент | 2394 | 10/22 |
| 7 | flipsimu.com/one-card-tarot/ | 43 | инструмент | 1215 | 9/14 |
| 8 | newagestore.com/free-tarot-readings/1-tarot-card/ | 33 | инструмент | 188 | 0/0 |
| 9 | forum.thetarot.guru/t/how-to-do-one-card-tarot-readings-that-wor | 9 | форум | — | — |
| 10 | thatoracleguy.com/one-card-tarot | 16 | инструмент | 738 | 1/0 |

Открыто страниц: 6 из 9 строк; текст посчитан у 5. **Медиана текста: ≈749 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Позиция 3 — AI Overview, в нём цитируются dailyom, labyrinthos, flipsimu. У tarot.com и dailyom страницы почти целиком на JS (сервер отдаёт 30–60 слов), текст не посчитан. micheleknight.com (#4) не открылась (ошибка соединения).

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 6 из 6
- FAQ: 4 из 6 (labyrinthos, flipsimu, onecardtarot.online, thatoracleguy)
- «Как сделать чтение / когда использовать»: 3 из 6 (flipsimu, onecardtarot.online, labyrinthos)
- Выбор колоды перед вытягиванием — у labyrinthos (#1)
- Перевёрнутые карты упоминаются в заголовке только у onecardtarot.online («Reversals»)

**Чего никто не делает хорошо:**
- Как читать выпавшую одну карту: почти все выдают текст карты и всё; пошаговой логики «ситуация → карта → вопрос себе» нет
- Что делать, если карта «плохая»
- Различие «карта на сейчас» и «карта дня» (все смешивают)

**Интенты (14):**
1. one card tarot yes no (350)
2. one card tarot reading yes or no (200)
3. one card tarot yes or no (150)
4. tarot one card yes or no (70)
5. one tarot card reading yes or no (30)
6. one card tarot pull yes or no (30)
7. pull a tarot card for me [карта страниц]
8. pull a random tarot card [карта страниц]
9. one card tarot with reversals [карта страниц]
10. how to shuffle tarot cards (2 200) [Ahrefs, тема]
11. how to do a one card tarot reading [H2 flipsimu]
12. when to use a one tarot card reading [H2 flipsimu]
13. tips for better one card tarot results [H2 flipsimu]
14. how people use one card tarot [H2 onecardtarot.online]

## EN-006 — Карта дня (US)

**Главный запрос:** «daily tarot» (объём не запрашивался; в карте страниц группа 3 100). Фичи выдачи: AI Overview (поз.5).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | dailytarotdraw.com/ | 42 | инструмент | 2607 | 31/27 |
| 2 | labyrinthos.co/pages/one-card-tarot | 67 | инструмент | 749 | 10/6 |
| 3 | tarot.com/daily-tarot-card | 71 | инструмент | 486 | 2/4 |
| 4 | free-tarot-reading.net/free | 40 | инструмент | 1509 | 4/18 |
| 6 | mytarottoday.com/ | 0 | инструмент | <100 (JS) | — |
| 7 | evatarot.net/ | 37 | инструмент | 514 | 2/1 |
| 8 | dailyom.com/tarot/one-card-reading | 71 | инструмент | не открыта | — |
| 9 | tellmytarot.com/daily-tarot/ | 12 | инструмент | 630 | 0/1 |
| 10 | horoscope.com/us/tarot/tarot-daily-love.aspx | 70 | инструмент | 141 | 2/3 |

Открыто страниц: 8 из 9 строк; текст посчитан у 7. **Медиана текста: ≈630 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Ahrefs по вопросам даёт почти нулевую частоту: интенты здесь собраны из заголовков и источников AI Overview, не из объёма. Поз. 5 — AI Overview; у него источники reddit и learntarot.com. 12 интентов — нижняя граница.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 8 из 8 открытых
- Короткий текст (<750 слов): 5 из 7 с посчитанным текстом (mytarottoday — JS); длинный только у dailytarotdraw.com (#1, 2 600 слов, 31 H2 — это целый портал) и free-tarot-reading.net
- Объяснение «как пользоваться ежедневным ритуалом»: 2 из 8 (dailytarotdraw «Daily Tarot Practice / Setting an intention», labyrinthos «A Daily Tarot Meditation»)
- Ссылка на другие расклады: большинство

**Чего никто не делает хорошо:**
- Возврат к карте: хранение карты на сутки, повторный визит — ни у кого в видимом тексте
- Смысл «карта дня» отдельно от «одна карта» (labyrinthos #2 — это страница one-card, Google её же ставит на daily)
- Как проверять день вечером

**Интенты (12):**
1. what is my tarot card of the day (0) [Ahrefs]
2. how to find the tarot card of the day (0) [Ahrefs]
3. what does tarot card of the day mean (0) [Ahrefs]
4. what is tarot card of the day (0) [Ahrefs]
5. what is the tarot card for each day of the week? (0) [Ahrefs]
6. how does tarot work (350) [Ahrefs, тема]
7. daily tarot draw [карта страниц]
8. tarot card of the day [карта страниц, ядро 3 100]
9. how do you interpret a daily tarot card? [reddit r/witchcraft, источник AI Overview]
10. daily tarot reading lesson [learntarot.com lesson 5, источник AI Overview]
11. daily tarot: setting an intention [H2 dailytarotdraw]
12. daily love tarot reading [horoscope.com, поз.10]

## EN-007 — Да или нет (US)

**Главный запрос:** «yes or no tarot» (самый сильный запрос; «tarot yes or no» 10 000, в карте страниц 42 000 по группе). Фичи выдачи: AI Overview (поз.4), видео (поз.8).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | horoscope.com/tarot/tarot-yes-no.aspx | 70 | инструмент | 141 | 2/3 |
| 2 | labyrinthos.co/pages/yes-no-tarot-reading | 67 | инструмент | 854 | 9/6 |
| 3 | reddit.com/r/tarot/comments/9q0914/how_to_perform_a_yes | 95 | форум | — | — |
| 5 | astrology.com/tarot/yes-no.html | 74 | инструмент | 186 | 2/1 |
| 6 | psychicsource.com/article/other-psychic-topics/yes-or-no-tarot | 57 | статья | 2629 | 11/4 |
| 7 | jobcannon.io/tarot/yes-no | 40 | инструмент | 661 | 5/0 |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 9 | evatarot.net/tarot-yes-no/ | 37 | инструмент | — | — |
| 10 | zodiacsign.com/tarot/yes-no/ | 66 | инструмент | 248 | 1/1 |

Открыто страниц: 6 из 9 строк; текст посчитан у 6. **Медиана текста: ≈454 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 4 — AI Overview, в нём цитируются darkforesttarotcards, psychicsource, labyrinthos, astrology.com, jobcannon, два видео YouTube, reddit. Видео YouTube на поз. 8 (DR 99) и два в источниках AIO. Первые три результата: horoscope.com и labyrinthos — инструмент почти без текста (141 и 854 слов), reddit — форум. PAA из выдачи по «yes or no tarot cards» (см. ниже), по «yes or no tarot» блок PAA не приходил.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 5 из 5 открытых инструментов
- Короткий текст (<900 слов): 5 из 6 открытых; исключение psychicsource (2 600 слов, 11 H2, это статья)
- FAQ про точность: jobcannon, psychicsource, mysticmag
- «Как задать вопрос»: jobcannon, psychicsource, labyrinthos
- Ответ в формате Yes / No / Maybe

**Чего никто не делает хорошо:**
- Прозрачное правило: почему именно этот ответ (только у jobcannon есть блок «какие карты значат да/нет»)
- Что делать с ответом «нет» или «пока неясно»
- Много сайтов не показывают, как работают перевёрнутые карты в да/нет

**Интенты (16):**
1. tarot yes or no (10 000)
2. online tarot reading yes or no (2 000)
3. tarot card yes or no (1 500)
4. tarot reading yes or no (1 000)
5. 7 tarot yes or no (800)
6. tarot cards yes or no (800)
7. free tarot reading yes or no (600)
8. one card tarot yes no (350)
9. should i do it yes or no tarot? [PAA]
10. what cards mean yes or no in tarot? [PAA]
11. can you use tarot for yes or no? [PAA]
12. are tarot cards accurate, yes or no? [PAA]
13. yes or no tarot accurate 100 percent [карта страниц]
14. how accurate is a yes or no tarot reading? [H2 jobcannon]
15. how to ask a good yes or no question [H2 jobcannon/psychicsource]
16. one-card or three-card yes or no reading [H2 jobcannon]

## EN-009 — Какие карты значат да и нет — список (US)

**Главный запрос:** «yes or no tarot cards» (1 200 (в карте страниц)). Фичи выдачи: AI Overview (поз.1), Похожие вопросы (поз.4, 4 шт.), видео (поз.8).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 2 | angelorum.co/uncategorized/yes-no-meanings-all-78-tarot-c | 34 | список/хаб | 1216 | 2/3 |
| 3 | reddit.com/r/tarot/comments/13eztbc/yes_vs_no_tarot_car | 95 | форум | — | — |
| 5 | dailyom.com/tarot/yes-no | 71 | инструмент | не открыта | — |
| 6 | tarotelements.com/answering-yes-no-questions-using-tarot/ | 27 | статья | 3186 | 15/4 |
| 7 | mysticmag.com/psychic-reading/which-tarot-cards-mean-yes-a | 77 | статья | 2969 | 6/11 |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 9 | lightwands.org/blog/your-guide-to-yes-or-no-tarot-readings | 10 | статья | 1026 | 4/5 |
| 10 | nostra-tarot.com/en/spread_types/yesno | 8 | инструмент | 309 | 10/0 |

Открыто страниц: 5 из 8 строк; текст посчитан у 5. **Медиана текста: ≈1216 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 1 — AI Overview (источник — тот же состав, что и по «yes or no tarot»). Реддит на поз. 3 с двумя саблинками. dailyom на #5 — инструмент без текста (JS).

**Блоки у большинства (по заголовкам открытых страниц):**
- Список карт: 3 из 5 (angelorum — 78 карт; mysticmag, tarotelements — «Major/Minor arcana that mean yes/no/maybe»); lightwands — 4 метода без списка
- Метод/как получить да-нет с перевёрнутыми картами: 3 из 5 (tarotelements, mysticmag, lightwands)
- Как задать вопрос: 3 из 5 (tarotelements, mysticmag, lightwands)
- FAQ: 2 из 5 (mysticmag, tarotelements)
- Метод в заголовке «мой собственный список»: tarotelements — личный подход, он стоит на поз. 6 (DR 27)

**Чего никто не делает хорошо:**
- Правило: на чём основано да/нет карты (сила карты, масть, стихия, вверх/вниз) — у большинства «просто потому что так принято»
- Единый список по всем 78 с коротким основанием для каждой — angelorum есть список, но без объяснений
- Нет такого, чтобы список был рядом с инструментом

**Интенты (16):**
1. what cards mean yes or no in tarot? [PAA]
2. should i do it yes or no tarot? [PAA]
3. can you use tarot for yes or no? [PAA]
4. are tarot cards accurate, yes or no? [PAA]
5. tarot cards yes or no (800) [Ahrefs]
6. yes or no tarot list [карта страниц]
7. yes or no tarot cards list [карта страниц]
8. yes no meanings of all 78 tarot cards [title angelorum]
9. which tarot cards mean yes, no, or maybe? [H2 mysticmag]
10. major arcana that mean yes, no and maybe [H2 mysticmag]
11. minor arcana that mean yes, no and maybe [H2 mysticmag]
12. how to obtain a yes or no answer with reversals [H2 tarotelements]
13. yes no tarot questions to avoid [H2 tarotelements]
14. including time frames in yes no tarot questions [H2 tarotelements]
15. yes vs no tarot cards [reddit r/tarot, поз.3]
16. thoughts on yes/no tarots? [reddit sitelink]

## EN-011 — Любовный расклад (US)

**Главный запрос:** «love tarot reading» (объём не запрашивался; в карте страниц группа 3 600). Фичи выдачи: AI Overview (поз.3), видео (поз.8).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | labyrinthos.co/pages/free-love-tarot-reading | 67 | инструмент | 826 | 11/5 |
| 2 | evatarot.net/love-tarot/ | 37 | инструмент | 171 | 2/1 |
| 4 | onecardtarot.online/love-tarot | 1 | инструмент | 2441 | 13/31 |
| 5 | free-tarot-reading.net/ | 40 | инструмент | — | — |
| 6 | deckaura.com/pages/love-tarot-reading | 58 | инструмент | 2776 | 10/12 |
| 7 | reddit.com/r/spiritualitytalk/comments/1rx6ohf/love_tar | 95 | форум | — | — |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 9 | solstarot.com/love-readings/ | 0 | инструмент | 1264 | 4/6 |
| 10 | tarotap.com/en | 52 | инструмент | 1117 | 2/30 |

Открыто страниц: 6 из 9 строк; текст посчитан у 6. **Медиана текста: ≈1190 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 3 — AI Overview (источники: onecardtarot.online, evatarot, horoscope.com, deckaura, solstarot). Видео YouTube на поз. 8.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 6 из 6
- FAQ: 4 из 6 (labyrinthos, solstarot, onecardtarot.online, deckaura)
- «Как задать вопрос про любовь / как это работает»: 4 из 6 (solstarot, onecardtarot.online, deckaura, labyrinthos)
- Расклад в 3–8 карт (3 card spread у deckaura/solstarot; 8 карт у evatarot)
- Сопутствующие инструменты (да/нет, одна карта, 5 карт «отношения»): 3 из 6

**Чего никто не делает хорошо:**
- Расклад про «двух людей» с разными фрагментами (я / он / между нами) — упомянут только у onecardtarot.online как блок
- Что делать после чтения: вопросы к себе, а не предсказание
- Честно про границы: «он вернётся?» без гарантий. Reddit-посты (#7) прямо спрашивают «а это вообще легально/точно?» — ни одна страница на этот вопрос не отвечает

**Интенты (14):**
1. free love tarot what is he thinking (700)
2. free love tarot reading yes or no (300)
3. does he love me tarot spread (100)
4. does he love me tarot (80)
5. does he love me tarot yes or no (80)
6. does he love me tarot free (60)
7. free tarot card reading love [карта страниц]
8. love tarot readings: are they legit? [reddit, поз.7]
9. has your love reading ever been accurate? [reddit sitelink]
10. thoughts on love readings? dos and don'ts [reddit sitelink]
11. how to ask the cards about love [H2 solstarot]
12. love tarot horoscope or a personal love reading? [H2 deckaura]
13. what one card can clarify in love [H2 onecardtarot.online]
14. when the question is about two people [H2 onecardtarot.online]

## EN-014 — Хаб: значения 78 карт (US)

**Главный запрос:** «tarot card meanings» (объём не запрашивался; в карте страниц группа 29 000 (с «tarot cards list», «how many cards in a tarot deck»)). Фичи выдачи: AI Overview (поз.2), Похожие вопросы (поз.6, 4 шт.), картинки (поз.9).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | labyrinthos.co/blogs/tarot-card-meanings-list | 67 | список/хаб | 2150 | 5/53 |
| 3 | thetarotlady.com/tarot-card-meanings/ | 52 | список/хаб | 832 | 54/0 |
| 4 | reddit.com/r/NonTheisticPaganism/comments/kzba6e/tarot_ | 95 | форум | — | — |
| 5 | lunafactory.com/blogs/tarot-card-meanings/tarot-complete-gui | 11 | статья | 2412 | 10/13 |
| 7 | biddytarot.com/tarot-card-meanings/ | 71 | список/хаб | не открыта | — |
| 8 | tarot.com/tarot/cards | 71 | список/хаб | 451 | 5/0 |
| 10 | tarotcake.com/tarot-card-meanings-the-major-arcana/ | 11 | список/хаб | 1210 | 3/23 |

Открыто страниц: 5 из 7 строк; текст посчитан у 5. **Медиана текста: ≈1210 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 2 — AI Overview (источники: lunafactory, tarotcake, labyrinthos, YouTube, quizlet, biddytarot, thetarotlady, tarot.com, reddit). Картинки на поз. 9 (Pinterest, Scribd, Etsy, Instagram, labyrinthos). Медиана — по страницам labyrinthos, thetarotlady, lunafactory, tarot.com, tarotcake; у labyrinthos в счёт входят и тексты на странице списка.

**Блоки у большинства (по заголовкам открытых страниц):**
- Список карт с переходом на страницу карты: 3 из 5 открытых (labyrinthos, thetarotlady, tarot.com)
- Деление на старшие/младшие, по мастям: 3 из 5 (labyrinthos, tarot.com, lunafactory)
- Введение «что такое карты Таро, сколько их»: lunafactory (статья 2 400 слов с FAQ, «5 mistakes»), labyrinthos
- FAQ: 3 из 5
- Кратких значений прямо в списке — только у части: thetarotlady (832 слов, 54 H2, одна строка на карту)

**Чего никто не делает хорошо:**
- Ответ на «сколько карт в колоде» (4 900/мес.) прямо вверху: PAA и AI Overview отвечают, а сами хабы прячут ответ
- Навигация «найди карту по запросу» (поиск/фильтр) — почти нигде
- biddytarot (DR 71, поз. 7) не открылась: защита от ботов

**Интенты (16):**
1. how to read tarot cards (6 000) [Ahrefs]
2. how many cards in a tarot deck (4 900) [Ahrefs]
3. what are tarot cards (3 400) [Ahrefs]
4. how many tarot cards are there (2 500) [Ahrefs]
5. are tarot cards evil (2 300) [Ahrefs]
6. how to shuffle tarot cards (2 200) [Ahrefs]
7. how to use tarot cards (1 800) [Ahrefs]
8. how many cards are in a tarot deck (1 300) [Ahrefs]
9. what do the tarot cards represent? [PAA]
10. what are the 12 main tarot cards? [PAA]
11. which is the strongest card in tarot? [PAA]
12. what are the 78 tarot cards and their meanings? [PAA]
13. tarot card meanings pdf [карта страниц]
14. tarot cards meaning list with pictures [карта страниц]
15. are there any websites with accurate meanings for each card? [reddit sitelink]
16. found a high quality, concise tarot card meanings [reddit sitelink]

## EN-093 — Старшие арканы (US)

**Главный запрос:** «tarot cards major arcana» (1 800 (в карте страниц)). Фичи выдачи: AI Overview (поз.1), Похожие вопросы (поз.4, 4 шт.), картинки (поз.9), видео (поз.8).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 2 | tarot.com/tarot/cards/major-arcana | 71 | список/хаб | 1669 | 24/4 |
| 3 | en.wikipedia.org/wiki/Major_Arcana | 97 | Википедия | 3622 | 8/2 |
| 5 | tarotcake.com/tarot-card-meanings-the-major-arcana/ | 11 | список/хаб | 1210 | 3/23 |
| 6 | reddit.com/r/Tarotpractices/comments/1dlkn7l/tarot_chal | 95 | форум | — | — |
| 7 | labyrinthos.co/blogs/tarot-card-meanings-list/tagged/major- | 67 | список/хаб | 759 | 3/23 |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 10 | thetarotguide.com/major-arcana/ | 44 | список/хаб | не открыта | — |

Открыто страниц: 4 из 7 строк; текст посчитан у 4. **Медиана текста: ≈1439 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Только 10 интентов: на эту страницу не хватило бюджета Ahrefs на вопросы (см. «Что не добрано»). Поз. 1 — AI Overview с 12 источниками, среди них две колоды Rider-Waite/Thoth в товарных карточках. thetarotguide.com (#10) не открылся: защита.

**Блоки у большинства (по заголовкам открытых страниц):**
- Список 22 карт с короткими значениями и ссылкой: 3 из 4 открытых (tarot.com, tarotcake, labyrinthos)
- Определение «что такое Major Arcana, сколько карт» вверху: tarot.com, wikipedia
- История (Википедия «History», «Esotericism»); у tarotcake — путь Дурака
- FAQ: 2 из 4
- Тон: tarot.com — «Tarot’s Big Mood Moments», 24 H2 на 22 карты

**Чего никто не делает хорошо:**
- Путь Дурака как сюжет: 22 карты как история — есть у tarotcake и в Reddit-обсуждении (#6, «story of the major arcana»), но коротко
- Сравнение старших и младших в двух строчках
- Как найти «свою» старшую аркану (PAA: «How do I find my Major Arcana?») — в открытых страницах отдельного блока нет

**Интенты (10):**
1. what are the 22 major arcana cards? [PAA]
2. how do i find my major arcana? [PAA]
3. what's the most powerful tarot card? [PAA]
4. what is 22 in the major arcana? [PAA]
5. tarot card meanings major arcana [карта страниц]
6. describe each major arcana card with one single keyword [reddit, поз.6]
7. how would you describe each of the major arcana? [reddit sitelink]
8. story of the major arcana [reddit sitelink]
9. history of the major arcana [Википедия, sitelink]
10. the fool's journey [тема tarotcake]

## ES-001 — Главная ES (MX)

**Главный запрос:** «tarot gratis» (объём не запрашивался; в карте страниц группа 12 000). Фичи выдачи: AI Overview (поз.6).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | tarot.run/es/reading/setup | 0 | инструмент | 481 | 5/0 |
| 2 | nostra-tarot.com/es/spread_types/day | 9 | инструмент | 239 | 10/0 |
| 3 | tarotap.com/es | 52 | инструмент | 1414 | 2/29 |
| 4 | tarotoo.com/es/tarot-gratis | 49 | инструмент | 1530 | 1/0 |
| 5 | espirituale.com/es/tarot | 0 | инструмент | 140 | 5/0 |
| 7 | ia.gratis/vida/tarot/ | 19 | инструмент | 1644 | 3/3 |
| 8 | losarcanos.com/ | 52 | инструмент | 2720 | 3/2 |
| 9 | tarotamigo.com/tarot/destino-completa/ | 26 | инструмент | 1263 | 7/0 |
| 10 | tarot-josnell.com/ | 10 | инструмент | не открыта | — |

Открыто страниц: 8 из 9 строк; текст посчитан у 8. **Медиана текста: ≈1338 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 6 — AI Overview, источники: tarotap, tarot.run, esotarot, trustedtarot, nostra, jobcannon, tarotoo. tarot-josnell.com (#10) не открылся (пустой ответ).

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 8 из 8
- FAQ: 7 из 8 (все, кроме losarcanos)
- «Как задать вопрос / как работает»: 3 из 8 (tarot.run, ia.gratis, tarotamigo)
- Выбор тирады на главной (Sí/No, Carta del día, Cruz celta): espirituale, nostra, tarot.run
- Тексты длиннее 1 200 слов: 5 из 8 (tarotap, tarotoo, ia.gratis, losarcanos 2 700, tarotamigo)

**Чего никто не делает хорошо:**
- В топе нет ни одного домена из Мексики: tarotap/tarotoo/jobcannon — переводы международных шаблонов, losarcanos/tarotamigo — Испания
- Тон «tarot gratis» по-мексикански: никто не объясняет, как отличаться от колод Мексики (Rider-Waite vs Marsella — почти нигде)
- Нет ясного правила «бесплатно/платно»

**Интенты (15):**
1. que es el tarot (1 300) [Ahrefs MX]
2. cuantas cartas tiene el tarot (1 000)
3. como leer el tarot (700)
4. tarot que es (600)
5. que es el tarot y para que sirve (500)
6. tarot si o no (4 000, соседний интент)
7. ¿cuál es el mejor tarot gratis? [PAA по «tarot gratis 3 cartas»]
8. ¿cuál es la mejor aplicación gratuita de tarot? [PAA]
9. ¿dónde puedo encontrar ChatGPT para leer tarot gratis en español? [PAA]
10. tirada completa gratis [карта страниц]
11. tarot online [карта страниц]
12. cómo hacer una buena pregunta de tarot [H2 tarot.run]
13. cómo elegir una tirada [H2 tarot.run]
14. qué aporta una tirada completa frente a una corta [H2 tarotamigo]
15. cuándo hacer una tirada de cartas gratis completa [H2 tarotamigo]

## ES-004 — Carta del día (MX)

**Главный запрос:** «tarot del dia» (объём не запрашивался; «tarot del dia de hoy» в карте страниц, суммарно 70). Фичи выдачи: нет AI Overview, нет PAA, нет видео.

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | aliciagalvan.com/tarot/tarot-gratis/la-carta-del-dia/ | 35 | инструмент | 776 | 1/1 |
| 2 | tarot.euroresidentes.es/carta_hoy | 29 | инструмент | 405 | 2/13 |
| 3 | tarot.eu/tarot/tarot-del-dia.php | 35 | инструмент | 1358 | 6/6 |
| 4 | mi.astrocentro.com/tarot/ | 42 | инструмент | 1810 | 8/19 |
| 5 | losarcanos.com/arcano_dia.php | 52 | инструмент | 1202 | 2/7 |
| 6 | astralgossip.com/es/carta-tarot-hoy/ | 0 | инструмент | не открыта | — |
| 7 | horoscopo.com/tarot/hoy-manana | 31 | инструмент | 523 | 3/9 |
| 8 | horoscopo.com/tarot/amor-diario | 31 | инструмент | 516 | 3/9 |
| 9 | cadizdirecto.com/tarot/carta-dia-gratis/ | 44 | инструмент | 3022 | 7/25 |
| 10 | marmaratarot.com/tarot-diario-gratuito | 29 | инструмент | не открыта | — |

Открыто страниц: 8 из 10 строк; текст посчитан у 8. **Медиана текста: ≈989 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Объём и вопросы Ahrefs по этому ядру не запрашивались (бюджет). Интенты из H2 топа и карты страниц. astralgossip (#6) и marmaratarot (#10) не открылись.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 8 из 8
- Короткий текст (<900 слов): 4 из 8
- «Как это работает / как сделать»: tarot.eu, cadizdirecto
- Смысл повторяющейся карты и «как применить к дню»: cadizdirecto (3 000 слов, 7 H2, 25 H3)
- Связь с гороскопом/любовью (horoscopo.com amor-diario, losarcanos «Horóscopo Diario»)

**Чего никто не делает хорошо:**
- Почти все — испанские домены (euroresidentes, cadizdirecto, marmaratarot, tarot.eu): мексиканский вариант никто не делает
- Возврат к карте дня
- Нет AI Overview и PAA — выдача старого типа: любой хорошо сделанный инструмент с коротким текстом может войти

**Интенты (14):**
1. tarot del dia de hoy [карта страниц]
2. tarot diario gratis [карта страниц]
3. carta del día tarot [карта страниц]
4. carta del tarot para hoy [title astralgossip]
5. tarot hoy/mañana [title horoscopo.com]
6. tarot de amor diario [title horoscopo.com]
7. qué significa tu carta del día [H2 cadizdirecto]
8. cómo hacer tu tirada de tarot diario gratis [H2 cadizdirecto]
9. cuando una carta se repite en tu consulta diaria [H2 cadizdirecto]
10. qué hacer cuando una carta del día no gusta [H2 cadizdirecto, обрезано]
11. cómo aplicar el mensaje de la carta a tu día [H2 cadizdirecto]
12. cómo funciona el tarot diario [H2 tarot.eu]
13. qué puedes preguntar al tarot sobre tu día [H2 tarot.eu]
14. tarot del día en 3 cartas [title astrocentro]

## ES-005 — Sí o no (MX)

**Главный запрос:** «tarot si o no» (4 000). Фичи выдачи: AI Overview (поз.2), видео (поз.10).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | losarcanos.com/tarot-si-o-no.php | 52 | инструмент | 1217 | 1/1 |
| 3 | nostra-tarot.com/es/spread_types/yesno | 8 | инструмент | 260 | 10/0 |
| 4 | tarotoo.com/es/tarot-si-no | 49 | инструмент | 1601 | 1/0 |
| 5 | jobcannon.io/es/tarot/yes-no | 40 | инструмент | 533 | 2/0 |
| 6 | aitarot.pro/es/tools/tarot/yes-no | 27 | инструмент | 522 | 3/11 |
| 7 | play.google.com/store/apps/details | 100 | приложение | — | — |
| 8 | juliantarot.com/es-419/tarot/yes-or-no | 18 | инструмент | 1479 | 6/8 |
| 9 | tarotap.com/es/yes-or-no-tarot | 52 | инструмент | 1178 | 5/27 |
| 10 | youtube.com/watch | 99 | видео | — | — |

Открыто страниц: 7 из 9 строк; текст посчитан у 7. **Медиана текста: ≈1178 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 2 — AI Overview с 8 источниками (tarotoo, jobcannon, tarotap, reddit, tiradastarotgratis, losarcanos, nostra). Видео YouTube на поз. 10.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 7 из 7
- Короткий текст (<700 слов): 3 из 7 (nostra 260, aitarot 522, jobcannon 533)
- FAQ: 6 из 7
- «Какие карты значат да / нет / depende»: jobcannon, juliantarot, tarotoo
- Выбор 1 или 3 карт: tarotap, juliantarot

**Чего никто не делает хорошо:**
- Прозрачное правило ответа — есть у jobcannon и juliantarot; остальные дают «ответ» без причины
- Мексиканский испанский: заголовки почти везде нейтральные/иберийские («tirada», «certero»)
- Приложения Google Play на #7 — значит, есть спрос на «мобильный» вариант

**Интенты (15):**
1. tarot si o no (4 000)
2. tarot si o no gratis (1 300)
3. tarot del si o no (500)
4. tarot gratis si o no (400)
5. tarot si o no 1 carta (350)
6. tarot si o no 1 carta gratis (200)
7. tarot si o no del amor (80)
8. tarot sí o no certero [title nostra]
9. tarot sí o no respuesta inmediata [title tarotap]
10. qué cartas del tarot significan sí, no o depende [H2 jobcannon, juliantarot]
11. cómo se decide sí, no o quizás [H2 juliantarot]
12. tarot de marsella sí o no: los 22 arcanos [H2 juliantarot]
13. cómo hacer el tarot sí o no gratis [H2 tarotap]
14. 1 carta o 3 cartas [H2 tarotap, juliantarot]
15. tarot si o no con 5 cartas gratis [tiradastarotgratis, источник AIO]

## ES-009 — Tarot del amor (MX)

**Главный запрос:** «tarot del amor» (500 в карте страниц; ядро «tarot del amor gratis» выше, не уточнялось). Фичи выдачи: AI Overview (поз.5), видео (поз.8), картинки-книги (поз.9).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | trustedtarot.com/es/tarot-del-amor/ | 50 | инструмент | не открыта | — |
| 2 | play.google.com/store/apps/details | 100 | приложение | — | — |
| 3 | losarcanos.com/amor.php | 52 | инструмент | 1456 | 1/6 |
| 4 | tarotoo.com/es/tarot-del-amor | 49 | инструмент | 1513 | 1/0 |
| 6 | horoscopo.com/tarot/amor-diario | 31 | инструмент | 516 | 3/9 |
| 7 | esotarot.es/tarot-amor/ | 39 | инструмент | 178 | 2/0 |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 10 | tarotamigo.com/tarot/amor/ | 26 | инструмент | 1924 | 9/7 |

Открыто страниц: 5 из 8 строк; текст посчитан у 5. **Медиана текста: ≈1456 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

trustedtarot.com (#1) не открылся: защита.

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 5 из 5
- Длинный текст у tarotamigo (1 900, 9 H2) и losarcanos/tarotoo (около 1 500)
- Блок «что можно спросить»: tarotamigo, trustedtarot (не открылся)
- FAQ: 2 из 5
- Любовь в формате «что он/она чувствует», «будущее ближайшее»: tarotamigo

**Чего никто не делает хорошо:**
- Любое обещание про «имя в расклад» — tarotamigo делает, но без объяснения как
- Сомнения про точность и «серьёзность» любовного таро
- Приложения Google Play (#2) и книги (картинки) показывают, что часть спроса — на «купить книгу/приложение», их не обслуживают

**Интенты (13):**
1. tarot del amor gratis [карта страниц]
2. tarot certero gratis futuro inmediato amor [карта страниц]
3. tarot gratis 3 cartas amor [карта страниц]
4. tarot si o no del amor (80)
5. tarot del amor si o no (30)
6. cual es la carta del amor en el tarot (10)
7. tarot del amor gratis que siente por mi (0)
8. que significa el colgado en el tarot del amor (0)
9. qué siente por ti ahora mismo según las cartas [H2 tarotamigo]
10. tarot del amor con nombres [H2 tarotamigo]
11. qué puedes preguntar en una tirada del tarot del amor [H2 tarotamigo]
12. cuando el amor no llega, qué puede revelarte [H2 tarotamigo]
13. tarot y amor: los 22 arcanos mayores [tarotnova, источник AIO]

## ES-099 — Тирада de 3 cartas (MX)

**Главный запрос:** «tarot gratis 3 cartas» (2 400). Фичи выдачи: AI Overview (поз.3), Похожие вопросы (поз.10, 4 шт.), видео TikTok (поз.8).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 1 | tarotoo.com/es/tarot-3-cartas | 49 | инструмент | 1245 | 1/0 |
| 2 | tarotfiable.es/tarot-gratis-3-cartas/ | 11 | инструмент | 5069 | 12/17 |
| 4 | tarotime.net/es/tirada-tarot-3-cartas-gratis/ | 3 | инструмент | не открыта | — |
| 5 | tarot.com/readings-reports/tarot-readings/free/love | 71 | инструмент | не открыта | — |
| 6 | tarotap.com/es/yes-or-no-tarot | 52 | инструмент | 1178 | 5/27 |
| 7 | tarotamigo.com/tarot/tres-cartas/ | 26 | инструмент | 1126 | 8/6 |
| 8 | tiktok.com/@veralmakeup/video/7641304740474653966 | 97 | видео | — | — |
| 9 | tiradastarotgratis.net/tiradas-tarot-gratis-tarot-de-marsella-tres- | 6 | инструмент | 632 | 2/2 |

Открыто страниц: 5 из 8 строк; текст посчитан у 5. **Медиана текста: ≈1178 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 3 — AI Overview (tarotoo, tarotia). tarotime (#4) не открылся (ошибка), tarot.com (#5) почти пустой (JS, 12 слов).

**Блоки у большинства (по заголовкам открытых страниц):**
- Инструмент выше текста: 5 из 5
- FAQ: 3 из 5 (tarotoo, tarotap, tarotamigo)
- «Что значит каждая позиция (прошлое-настоящее-будущее)»: tarotamigo, tarotfiable (+ tarotia, из AI Overview, не из топ-10)
- Длинная статья про Таро: tarotfiable (5 000 слов, 12 H2) — но он на #2 с DR 11
- Колода: Marsella или española: tarotamigo, tiradastarotgratis, tarotoo

**Чего никто не делает хорошо:**
- Как понимать три карты вместе (сочетание карт) — все рассказывают позиции, но не связь
- Расклады не только прошлое-настоящее-будущее (ситуация-препятствие-совет)
- Ответ на «cómo leer el tarot con 3 cartas?» (PAA) на самих страницах-инструментах слабый: позиции есть, сочетание карт нет

**Интенты (14):**
1. ¿cuál es el mejor tarot gratis? [PAA]
2. ¿cuál es la mejor aplicación gratuita de tarot? [PAA]
3. ¿dónde puedo encontrar chatgpt para leer tarot gratis en español? [PAA]
4. ¿cómo leer el tarot con 3 cartas? [PAA]
5. tarot gratis 3 cartas (2 400) [карта страниц]
6. tirada de 3 cartas gratis [карта страниц]
7. tarot 3 cartas gratis [карта страниц]
8. pasado, presente y futuro [title tarotime, tarotia]
9. tarot gratis 3 cartas: amor, dinero y salud [TikTok, поз.8]
10. qué representa cada carta en la tirada de 3 cartas [H2 tarotamigo]
11. preguntas para una tirada de 3 cartas [H2 tarotia]
12. para qué sirve el tarot gratis de 3 cartas [H2 tarotamigo]
13. por qué la baraja española para una tirada de 3 cartas [H2 tarotamigo]
14. tarot de marsella con tres cartas [title tiradastarotgratis]

## ES-012 — Cartas del tarot — хаб 78 карт (MX)

**Главный запрос:** «cartas del tarot» (3 300 (в карте страниц)). Фичи выдачи: AI Overview (поз.1), Похожие вопросы (поз.6, 4 шт.), картинки.

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 2 | thetarotlady.com/tarot-card-meanings/ | 52 | список/хаб | 832 | 54/0 |
| 3 | es.wikipedia.org/wiki/Tarot_(adivinaci%C3%B3n) | 97 | Википедия | 5141 | 9/18 |
| 4 | listado.mercadolibre.com.mx/otras-categorias/esoterismo/cartas-tarot/ | 87 | магазин | — | — |
| 5 | darkforesttarotcards.com/es-es/blogs/news/tarot-card-meanings-complet | 5 | статья | 9067 | 6/53 |
| 8 | lecturas.com/horoscopo/astrologia/tarot-significado-78-ca | 69 | статья | не открыта | — |
| 9 | tarotap.com/es/draw-cards | 52 | инструмент | 1190 | 5/33 |
| 10 | astrolink.com/es/tarot | 43 | список/хаб | 1501 | 4/3 |

Открыто страниц: 5 из 7 строк; текст посчитан у 5. **Медиана текста: ≈1501 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 1 — AI Overview, источники: Wikipedia, tarotap draw-cards, lecturas, V&A (музей), darkforest, jobcannon, astrolink, Instagram. Поз. 4 — MercadoLibre (магазин колод). lecturas.com (#8) не открылась (403).

**Блоки у большинства (по заголовкам открытых страниц):**
- Список с переходом на карты: thetarotlady, astrolink, darkforest
- Определение «что такое Таро, сколько карт»: wikipedia, astrolink, darkforest
- FAQ: 2 из 5 (darkforest, tarotap)
- Деление на 22 старших и 56 младших: darkforest, astrolink, lecturas
- Один сайт выдаёт 9 000 слов (darkforest) — как «каталог»

**Чего никто не делает хорошо:**
- Топ — переводы (thetarotlady, darkforest) и испанские/общие сайты; специализированного мексиканского хаба нет
- Прямой ответ «сколько карт в Таро» вверху
- Нет формата «найди карту по названию»

**Интенты (14):**
1. ¿cuáles son las 22 cartas del tarot? [PAA]
2. ¿cuáles son las 12 cartas del tarot? [PAA]
3. ¿cómo se llaman las 78 cartas del tarot? [PAA]
4. ¿qué significa cada una de las cartas del tarot? [PAA]
5. cuantas cartas tiene el tarot (1 000)
6. cuantas cartas del tarot son (200)
7. como leer las cartas del tarot (150)
8. como se leen las cartas del tarot (80)
9. cuales son las cartas del tarot (60)
10. como interpretar las cartas del tarot (60)
11. significado de las 78 cartas del tarot de marsella [карта страниц]
12. cuántos tipos de cartas hay en el tarot [Instagram, источник AIO]
13. cómo leer las cartas con esta guía [H2 darkforest]
14. tu mazo importa [H2 darkforest]

## ES-091 — Arcanos mayores (MX)

**Главный запрос:** «arcanos mayores» (1 800 (в карте страниц)). Фичи выдачи: AI Overview (поз.1), Похожие вопросы (поз.3, 4 шт.), картинки, видео (поз.8, 9).

| Поз. | Страница | DR | Тип | Слов | H2/H3 |
|---|---|---|---|---|---|
| 2 | astrolink.com/es/tarot/arcanos-mayores | 43 | список/хаб | <100 (JS) | — |
| 4 | es.wikipedia.org/wiki/Triunfos_(tarot) | 97 | Википедия | 3071 | 7/1 |
| 5 | vogue.mx/articulo/arcanos-mayores-del-tarot | 76 | статья | 5774 | 7/0 |
| 6 | universodeletras.unam.mx/2021/09/arcanos-mayores/ | 88 | статья | 420 | 0/1 |
| 8 | youtube.com/watch | 99 | видео | — | — |
| 9 | facebook.com/glucmx/videos/los-arcanos-mayores-son-las-22 | 100 | видео | — | — |
| 10 | tarotnova.app/es/blog/22-arcanos-mayores-tarot-de-marsella | 16 | статья | 1966 | 8/30 |

Открыто страниц: 5 из 7 строк; текст посчитан у 4. **Медиана текста: ≈2518 слов** (всё на странице вне меню и подвала, с шумом ±20%; у сайтов с картами/списками внутри — включая тексты карт).

Поз. 1 — AI Overview с 12 источниками. astrolink (#2) отдаёт список почти целиком на JS (87 слов), в медиану не вошёл. Видео: YouTube (#8) и Facebook (#9).

**Блоки у большинства (по заголовкам открытых страниц):**
- Определение «что такое arcanos mayores» вверху: 4 из 4 открытых (wikipedia, vogue, unam, tarotnova)
- Описание 22 карт: 2 из 4 (vogue, tarotnova); у цитируемых AI Overview, но вне топ-10 arcanojoyeria и velvetastral — тоже
- «Как читать арканы»: tarotnova, vogue; про перевёрнутые — velvetastral (вне топ-10)
- FAQ: 3 из 4 (vogue, unam, tarotnova)
- Группировка по трём этапам пути Дурака (0–VII, VIII–XIV, XV–XXI): velvetastral (вне топ-10, источник AI Overview)

**Чего никто не делает хорошо:**
- Мексиканские домены есть только в виде медиа (vogue.mx, unam.mx) — специализированных мексиканских нет
- Ответ на «сколько арканов mayores» одной строкой + ссылки на каждую
- Как найти «свой» аркан — PAA задаёт вопрос, на страницах только vogue («¿Cómo saber cuál es tu carta del tarot?»)

**Интенты (15):**
1. ¿cuáles son los 22 arcanos mayores del tarot? [PAA]
2. ¿cuáles son los 11 arcanos mayores? [PAA]
3. ¿cómo saber cuál es mi arcano mayor? [PAA]
4. ¿cuáles son los 9 arcanos mayores? [PAA]
5. cuantos arcanos mayores hay (300)
6. cuántos arcanos mayores hay (90)
7. cuales son los arcanos mayores del tarot (80)
8. cuales son los arcanos mayores (70)
9. cuantos arcanos mayores hay en el tarot (60)
10. cuáles son los 22 arcanos mayores del tarot (50)
11. 22 arcanos mayores [карта страниц]
12. cómo saber cuál es tu carta del tarot [H2 vogue]
13. qué significa que salgan varios arcanos mayores [H2 velvetastral]
14. cómo leer los arcanos mayores invertidos [H2 velvetastral]
15. el viaje del loco [H2 arcanojoyeria]


---

## Сводка по типам страниц

### Медианы текста вокруг инструмента / в списке

| Тип | Страницы | США | Мексика |
|---|---|---|---|
| Инструмент-расклад (главная, один/три) | EN-001, EN-005, ES-001, ES-099 | ≈ 750–990 | ≈ 1 180–1 340 |
| Ежедневный | EN-006, ES-004 | ≈ 630 | ≈ 990 |
| Да / нет | EN-007, ES-005 | ≈ 450 | ≈ 1 180 |
| Любовь | EN-011, ES-009 | ≈ 1 190 | ≈ 1 460 |
| Список «да/нет по картам» | EN-009 | ≈ 1 220 | — |
| Хаб значений 78 карт | EN-014, ES-012 | ≈ 1 210 | ≈ 1 500 |
| Старшие арканы | EN-093, ES-091 | ≈ 1 440 | ≈ 2 500 (по 4 страницам) |

### Кому нужен длинный текст, кому нет

- **Мало текста (≤ 700 слов)** — «да/нет» в США, «одна карта», «карта дня» в США. Верх выдачи — почти пустые страницы с инструментом (horoscope.com, labyrinthos, dailyom, tarot.com). Здесь выигрывает скорость и ясность инструмента.
- **Средний текст (900–1 500)** — главная, три карты, любовь, весь испанский рынок инструментов. Нужны FAQ и «как это работает».
- **Много текста (1 200–2 500+)** — списки и хабы: «да/нет по картам», «все карты», «старшие арканы». Это страницы-справочники, текст держится на списке и на прямом ответе на «сколько карт / сколько арканов».
- В Мексике длиннее везде: FAQ есть практически у каждой страницы, а плотность вопросов в PAA выше.

### Типичные H2 по типам

- **Инструмент-расклад:** «Как работает чтение», «Как задать вопрос», «Что значат позиции карт» (три карты), «Какая колода», «Точность и ограничения», «Частые вопросы».
- **Да/нет:** «Как работает / правило ответа», «Какие карты значат да, нет, пока неясно», «Как задать хороший вопрос», «Одна карта или три», «Насколько точно», «Частые вопросы».
- **Карта дня:** «Что значит карта дня», «Как сделать», «Что если карта повторяется», «Как применить к дню».
- **Любовь:** «Как задать вопрос про любовь», «Что значит расклад», «Для каких ситуаций подходит», «Частые вопросы».
- **Хаб 78 карт:** «Что такое Таро и сколько карт», «Старшие арканы», «Младшие арканы по мастям», «Как читать значения», «Частые вопросы».
- **Старшие арканы:** «Что такое старшие арканы, сколько их», «Путь Дурака (три этапа)», «Список 22 карт», «Как читать», «Частые вопросы».

### Три вывода, которые сильнее всего влияют на объём текста

1. **Инструментам в США лишний объём не помогает.** Первые места по «yes or no tarot», «one card tarot», «daily tarot» держат страницы на 140–850 слов, длинные лежат на 6–9 местах. Хватит 450–900 слов с FAQ. У любви планка выше (≈ 1 200).
2. **В Мексике планка выше и конкуренты слабые.** Медиана ≈ 1 000–1 450 слов с FAQ почти у всех, DR 0–52, нет мексиканцев. Нужны 1 200–1 500 слов на мексиканском испанском. Исключение — «carta del día»: пустая выдача без AI Overview, достаточно ≈ 800–1 000 слов.
3. **Хабам нужен прямой ответ вверху и список.** AI Overview и «Похожие вопросы» стоят над всеми 4 хабами; PAA — «сколько карт», «какие 22», «как найти свой аркан». Старшие арканы в Мексике: топ — длинные статьи 2 000–5 800 слов (Vogue, UNAM, Tarot Nova) — планка выше, чем в США (≈ 1 200–1 700).
