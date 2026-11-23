# Этап 5. Образцы страниц карт: заметки к черновикам

Актуальное состояние образцов — в разделе «После проверки Fable» в конце файла; разделы ниже до него описывают первые черновики.

22.11.2026. Четыре образца по шаблону из `10-card-serp-study.md` (раздел 8) с поправками владельца от 22.11
(объём ниже, ES-заголовки вопросами, одна строка соответствий Golden Dawn, без здоровья и сроков) и с учётом
`11-blocked-pages-check.md`. Статус всех файлов — `draft`, ничего не закоммичено.

Файлы:
- `content/cards/pages/en/major-00-fool.json`, `content/cards/pages/es/major-00-fool.json`
- `content/cards/pages/en/swords-03-three.json`, `content/cards/pages/es/swords-03-three.json`

## На чём основан каждый блок

Источник фактов — папка `content/sources/waite-pictorial-key/` (метки `[p. N]`); файл
`content/sources/waite-pictorial-key.txt` не использовался и не правился.

| Блок | The Fool / El Loco | Three of Swords / Tres de Espadas |
|---|---|---|
| `capsule` | ключевые слова и `yes_no_why` из `meanings.*.json`, вердикт из `deck.json` (yes) | то же (no) |
| `on_the_card` | Уэйт, p. 152, 155 (рисунок), p. 161 (сумка, «знаки»), p. 29 (старые колоды: животное нападает); цвет розы/неба и «0» — по скану 1909 | Уэйт, p. 248 (8 слов описания + «too simple and obvious»); расположение мечей, косой дождь, «III» — по скану 1909 |
| строка соответствий | Golden Dawn: стихия Воздух — помечено «не Уэйт» | Golden Dawn: Сатурн в Весах — помечено «не Уэйт» |
| `waite` | p. 286–287 (список значений), p. 161, 155, 309–310 | p. 248 (прямое и перевёрнутое) |
| `upright`, `reversed` | `meanings.*.json` (upright/reversed) + связка со списком Уэйта; где чтение современное — сказано прямо | то же |
| `love` | `meanings.*.json` (love), одинокие / в паре / перевёрнутая; без утверждений о партнёре | то же |
| `work_money` | современное чтение; деньги — «прогноза нет, посмотри на свой подход» (З3) | то же |
| `advice` | `advice` из `meanings.*.json` | то же |
| `yes_no` | `deck.json` yes + `yes-no-rules.json` (перевёрнутая → «Not clear yet» / «Todavía no está claro»), причина из `yes_no_why` | `deck.json` no + то же правило |
| `in_a_reading` | «как человек» (роль, не реальный человек) и «как чувство» о своей ситуации; без «итога» | то же |
| `combinations` | 4 пары по значениям проекта (Mago, As de Bastos, Dos de Espadas, Mundo); вступление — Уэйт p. 309–310 только в блоке `waite` | 4 пары (Cuatro, Seis, Dos de Espadas, Tres de Copas) |
| `not_to_confuse` | As de Bastos (Уэйт p. 196) | Nueve de Espadas (p. 236, только рисунок) и Cinco de Copas (p. 216) |
| `faq` | EN: 4 вопроса PAA из `card-serp-raw.json` (`en_fool`). ES: 3 PAA (`es_loco`) + «como sentimiento» (H2 у Dark Forest) + «qué número» (Lecturas, PAA `es_enamorados`) | EN: 3 PAA (`en_three`) + «how someone sees you» (PAA, ответ о своей стороне). ES: 3 PAA (`es_tres`) + «sí o no» и «en el amor» (заголовки топа и вопросы других карт MX) |
| `about_this_page` | скан 1909 Roses & Lilies (Wikimedia Commons), книга Уэйта со страницами, «написано с ИИ по книге Уэйта, проверено более сильной моделью ИИ, отредактировано редакцией Arcana Diary»; Марсель — иначе (З6) | то же + «не испанская колода» (выдача MX путает с baraja española) |
| `related` | 01 Mago, 21 Mundo, As de Bastos, Dos de Espadas (у Шута нет масти и номера) | 02 и 04 Espadas, Тройки остальных мастей |

## Title / description (c03.02, стр. 189–193)

| Страница | Title, знаков | Description, знаков |
|---|---|---|
| EN The Fool | 53 | 155 |
| ES El Loco | 50 | 155 |
| EN Three of Swords | 60 | 160 |
| ES Tres de Espadas | 58 | 155 |

Title — по формуле шаблона (сущность первой, один квалификатор «Upright, Reversed & Love» / «significado,
invertida y amor», без бренда). Description — факты (ключевые слова прямо/перевёрнуто), «Waite 1911 / 1909»,
в конце следующий шаг («Draw it for your question» / «Sácala para tu pregunta»). Капсулы 51–59 слов (c05.06,
стр. 452–453). Вступлений «In today's world» и выводов «In conclusion» нет, опыта от первого лица и выдуманных
авторов нет (c05.06, правила 2 и 5). Таблицы в схеме нет: ключевые слова — 2 списка, их рендерит этап 6 как
`<table>` (c03.03, стр. 202–206).

## Проверка запретов

`app.reader.check`: `load_reader_terms` → `live_terms(terms, lang, 'ok')` → `find_claims` по title, description,
h1, капсуле, каждому заголовку и абзацу, каждому вопросу и ответу FAQ и `waite.note`. Итог: **0 срабатываний,
0 «negated»** на всех 4 страницах. Дополнительно прогнали строгий словарь (с `en_redirect`/`es_redirect`) —
тоже 0. Ручной проход: нет дат и сроков, гарантий, «судьбы», чувств/мыслей другого человека (даже в отрицании),
прогнозов здоровья/денег/суда, специалистов; в ES нет родовых форм о читателе и «invertida» в теле текста
(только в title/description, как ищут).

## Объём (слов, по `word_count` из `check.py`)

| Страница | Всё на странице (H1, заголовки, вопросы FAQ) — поле `word_count` | Только текст (капсула, абзацы, ответы FAQ) | Цель владельца |
|---|---|---|---|
| EN The Fool | 1 806 | 1 685 | 1 200–1 800 |
| ES El Loco | 1 856 | 1 715 | 1 200–1 800 |
| EN Three of Swords | 1 490 | 1 330 | 900–1 400 |
| ES Tres de Espadas | 1 567 | 1 415 | 900–1 400 |

Текст укладывается в цели; с заголовками-вопросами испанские страницы чуть выше (заголовки ES длиннее).

## Где не уверен (решить владельцу)

1. **Страница Тройки Мечей у Уэйта — p. 248, а не 249.** В файлах метка `[p. N]` стоит *перед* текстом
   страницы (файл начинается с `[p. 57] PART II…` и кончается текстом, а не меткой), а «SWORDS / Three» идёт
   после `[p. 248]`. Пустые нечётные страницы между картами — вероятно, страницы с иллюстрацией. Везде указано
   p. 248; стоит сверить со сканом Wikisource. По той же логике Шут: описание p. 152 и 155, значения p. 286–287.
2. **Цитата Уэйта в ES-страницах — на английском** (дословно, как требует поле `quote`), объяснение
   по-испански своими словами; в абзацах ES Уэйт пересказан без кавычек, чтобы не выдавать перевод за цитату.
   Если нужен перевод цитаты — пометить «traducción nuestra».
3. **Детали по скану 1909** (белая роза, жёлтое небо, «0»/«III», расположение мечей, косой дождь) — не из книги
   Уэйта, а наблюдение по картинке, которую страница сама показывает. Если строго «только Уэйт» — убрать.
4. **Golden Dawn** (Шут — Воздух; Тройка Мечей — Сатурн в Весах): общеизвестные атрибуции, но источника в папке
   `content/sources/` нет. Нужно добавить источник (например, «Book T» / Liber 777) или убрать строку.
5. **Издание:** пишем «(1911)», как в разборе; README источника — первое издание 1910 (на титуле 1911),
   транскрипция Wikisource 1910/1922 — номера страниц по ней.
6. **Редактор:** в `11-blocked-pages-check.md` упомянуто решение владельца об имени редактора — по заданию
   имён не ставили, написано «Arcana Diary editor» / «equipo editorial de Arcana Diary». Подставить имя, когда
   будет решено.
7. **FAQ ES «como sentimiento», «qué número», «sí o no» (для Тройки), «en el amor» (для Тройки)** — не из PAA
   именно этой карты, а из заголовков страниц топа и PAA других карт MX. Вопрос Тройки «how someone sees you»
   отвечен о своей стороне без догадок о другом человеке — проверить, устраивает ли такая подача.
8. Испанский писан сразу по-мексикански, но вычитку носителем шаблон всё равно требует (раздел 6 разбора).

## После проверки Fable

22.11.2026. Применены все замечания из `21-card-samples-review.md` (Critical 1, Important 20) и Minor, с которыми
согласен; решения владельца от 22.11 — обязательны. Правила для остальных 76 карт — `30-card-page-rules.md`,
проверка — `tools/cards/check_pages.py`. Ничего не закоммичено; все страницы `status: "draft"`.

### Что изменилось

**Схема (`schema: 2`) и шаблон.**
- Новые поля: `editor: "{editor_name}"`, `reviewed_at: null`, `name_forms`, `image_alt`, `facts` (копия
  `deck.json`, без соответствий), `mentions` (имена других карт в тексте → ссылки), `citations` (дословные выписки
  Уэйта для каждой ссылки на страницу), `sources[].kind/url/pages`; в `waite` — `quote_lang`, `pages`,
  `translation`, `harsh`. Убраны `word_count` (считает скрипт) и `waite.note`.
- Общие строки вынесены в `content/cards/pages/template-strings.json` (обзор, изм. 2): правило «да/нет», вводная к
  сочетаниям, оговорка «роль, а не человек / твоя сторона», строка о деньгах, граница «дальше — современное
  чтение» (О1), фраза о тяжёлых словах, CTA, «About this page» с `{editor_name}` и `{reviewed_at}` (К1, решение 5),
  строка фактов, подписи. Блоки `draw_cta` и `about_this_page` из JSON карт убраны, `yes_no` — без абзацев,
  `combinations` — `pairs` с `card_id` (таблица и ссылки на этапе 6).
- Golden Dawn (Воздух, Сатурн в Весах) удалён целиком (решение 3; О4).

**Тексты (обе карты, оба языка).**
- Метки «In modern readings» / «En las lecturas modernas» в начале блоков убраны — одна граница в шаблоне (О1).
- FAQ без повторов H2 (О2); обязательный «good or bad / buena o mala» во всех четырёх. EN Шут: «good or bad», «Does
  The Fool mean I am being foolish?», «strongest», «0 or 21?» (место в колоде по pp. 29, 161); ES Loco: «buena o
  mala», «si te sale», «qué número», «¿…una locura?»; EN Тройка: «good or bad», «always heartbreak», «how do they
  see me» (короче, 2.3.7), «friendship»; ES Tres: «qué significa», «buena o mala», «siempre ruptura», «amistad».
- `in_a_reading` без каркаса «As a person… / As a feeling…» (О3); четвёртая фраза капсулы построена по-разному.
  Совпадение пятисловных цепочек между картами: было 11,5 % (EN) и 13,5 % (ES), стало 0,8 % и 0,7 %.
- Страницы: «(pp. 29–30)» для нападения животного (2.1.1, 2.2.1); `about`/`sources` — точный список страниц вместо
  «152–161» (О5); «Divinatory Meanings:» из цитаты убрано (2.3.4, 2.4.9).
- Шут: добавлено солнце со словами Уэйта «knows whence he came, whither he is going» (pp. 152–155) и «His countenance
  is full of intelligence and expectant dream» (p. 152) (2.1.2, 2.2.2); «his dog is still bounding» и «artificial
  and arbitrary» (p. 287) — из источника; сумка — его словами о «sub-conscious memories» (p. 161).
- Тяжёлые слова (решение 4; О6): у Шута (mania, delirium, frenzy) и Тройки (mental alienation) цитата дословно,
  `harsh: true`, после неё строка шаблона; выдуманная справка «alienation meant being set apart» удалена (2.3.1,
  2.4.1); в абзацах этих слов нет. Цитата Тройки теперь включает и перевёрнутый список (« … Reversed: …»).
- ES: полный перевод цитаты в `waite.translation` (2.2.3, 2.4.2; решение 7); «extravagancia» → «exceso» (2.2.4);
  «representa el viaje hacia afuera» (2.2.5); «orilla» → «borde» (2.2.10); «bastón grueso» (2.2.12); «espontaneidad»
  в капсуле (2.2.8); все кальки из таблицы раздела 4; имя карты во всех H2 Тройки, описание рисунка — «¿Qué hay en la
  carta del Tres de Espadas y qué simbolizan las espadas?» (2.4.4, 2.4.5); «lo cruzan» относится к сердцу (2.4.6);
  description — «al derecho y al revés (carta invertida)» + ключевое слово (2.2.7, 2.4.7).
- EN: «release» вернулось в текст (2.3.2); капсулы с причиной вердикта (2.1.3, 2.3.3, 2.4.8); «extravagance» не
  связано с деньгами от имени Уэйта (2.1.4); Five of Cups — слова Уэйта отделены от современного чтения (2.3.5);
  «Spanish deck» в EN убран (2.3.10, строка шаблона).
- Символы без опоры в базе убраны: «In modern readings the heart stands for feeling and the swords for hard words»
  (изм. 15).

### Что не принято и почему

- **Book T и `correspondences.json` (изм. 5, сомнение 4)** — заменено решением владельца 3: строки соответствий нет
  вовсе. Стихию масти в строку фактов тоже не ставлю: это та же традиция без источника в репозитории.
- **«Выбирать фрагмент цитаты без тяжёлых слов» (изм. 6)** — заменено решением 4: цитируем дословно + фраза шаблона.
- **Текст обзора для Тройки «"Mental alienation" is a harsh phrase of Waite's time…» (2.3.1, 2.4.1)** — вместо
  него единая фраза шаблона (решение 4) и в абзаце «on Arcana Diary that side of the card stands only for
  scattered, restless thoughts».
- **Перевод «distribution» как «dispersión» (2.2.3)** — дал «reparto»: «dispersión» — толкование, и это слово уже
  есть в списке Тройки как перевод «dispersion».
- **Год во фразе о тяжёлых словах** — «1911», а не «1910» из примера владельца: на странице везде «(1911)», иначе
  читатель увидит два года. Если владелец хочет «1910» — одна правка в `template-strings.json`.
- **Оба вопроса «positive?» и «bad?» у EN Шута (2.1.5)** — свёл в один обязательный «good or bad», освободившееся
  место отдал «0 or 21?» (как советует раздел 4 обзора).
- **Title Тройки в 60 знаков (2.3.8)** — оставлен: предел ≤ 60 соблюдён; резервная формула нужна 17 картам EN и 4 ES
  (список — `30-card-page-rules.md`, раздел 8).
- «(1911)» и номера по Wikisource (сомнение 5) — оставлены; ссылка на Wikisource добавлена в `sources`, строка о
  нумерации — в шаблоне. Сверку 2–3 страниц со сканом Wikisource сделать не мог (нет сети).

### Ложные друзья, проверенные в ES

extravagance → exceso (не «extravagancia»); intoxication → embriaguez (не «intoxicación»); mental alienation →
enajenación mental; distraction → distracción (в пояснении — «pensamientos dispersos»); distribution → reparto;
removal → alejamiento (не «remoción»); principle → principio; absence → ausencia; delay → demora; stout → grueso (не
«firme»); commit → comprometerte (так верно); reading / spread → lectura / tirada. В текстах нет «realizar» (realize),
«actualmente», «eventualmente», «sensible», «soportar», «embarazada», «asistir». Род о читателе: нейтральные
обороты («si no tienes pareja», «si eres tú», «sin culpar a nadie»); «usted» нет.

### Объём (слов текста без заголовков и вопросов FAQ: карта + строки шаблона)

| Страница | Текст карты | Шаблон | Итого | Предел |
|---|---|---|---|---|
| EN The Fool | 1 412 | 207 | **1 619** | ≤ 1 650 |
| ES El Loco | 1 384 | 234 | **1 618** | ≤ 1 650 |
| EN Three of Swords | 1 051 | 206 | **1 257** | ≤ 1 300 |
| ES Tres de Espadas | 1 055 | 230 | **1 285** | ≤ 1 300 |

Title / description: EN Fool 53 / 155, ES Loco 50 / 157, EN Three 60 / 156, ES Tres 58 / 147.

### Проверки

- `python3 -I tools/cards/check_pages.py` — все 4 страницы «OK», без предупреждений, код 0; совпадения между
  картами ≤ 0,8 %; шаблонные строки проходят оба словаря запретов.
- Запреты: строгий словарь `reader_banned_terms.json` (с `*_redirect`) и `tools/cards/banned_terms.json` по всему
  тексту карты (кроме цитаты Уэйта) — 0 срабатываний.
- Все цитаты и 16/5 выписок `citations` (Шут/Тройка) найдены дословно на указанных страницах источника.
- `api/.venv/bin/pytest -q tools/cards` — 110 passed (37 новых в `test_check_pages.py`); `pytest -q tools` — 208
  passed; `python3 -I tools/cards/validate_cards.py` — OK.

### Открытые вопросы

1. Год во фразе о тяжёлых словах: «1911» (как сейчас) или «1910» (как в примере владельца)?
2. Адреса Wikisource и Commons в `sources[].url` собраны по правилу (название файла из `sources.json`, главная
   страница книги) и не открывались — проверить на этапе 6.
3. Перевод «distribution» → «reparto» и «distraction» → «distracción»: старинный смысл у Уэйта неясен, переводим
   дословно; при вычитке носителем — посмотреть первыми.
