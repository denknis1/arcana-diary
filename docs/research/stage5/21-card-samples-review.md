**Вердикт: можно после правок.** Образцы переделывать не нужно: цитаты Уэйта дословные, номера страниц (кроме одного) верные, запреты сайта соблюдены, данные проекта не искажены. Но до того как писать по ним остальные 76 карт, надо поправить шаблон (раздел 3) — иначе его слабые места размножатся на 156 страниц.

# Этап 5. Проверка четырёх образцов страниц карт

22.11.2026. Проверены: `content/cards/pages/en/major-00-fool.json`, `es/major-00-fool.json`,
`en/swords-03-three.json`, `es/swords-03-three.json` и заметки `20-card-samples-notes.md`.

Счёт замечаний: **Critical — 1** (общее для всех 4 страниц), **Important — 20** (6 общих + 14 по страницам:
EN Fool 2, ES Loco 6, EN Three 2, ES Tres 4), **Minor — 28** (6 + 7 + 8 + 7).

## 0. Что проверено и как

| Что | Как | Итог |
|---|---|---|
| Цитаты Уэйта | каждая сверена с `content/sources/waite-pictorial-key/part-1…3.txt` посимвольно | все дословные, каждая ≤ 25 слов |
| Номера страниц | по меткам `[p. N]` (метка стоит перед текстом страницы) | верны все, кроме одного: p. 29 → pp. 29–30 |
| Детали «по карте 1909» | открыты сканы `site/public/cards/the-fool.webp` и `three-of-swords.webp` | всё подтверждается: роза белая, небо жёлтое, «0» вверху; одна шпага вертикально, две наискось, косой дождь, «III» вверху, сердце красное, небо серое |
| Данные проекта | `deck.json`, `meanings.en/es.json`, `yes-no-rules.json` | вердикты (yes / no), подписи «Not clear yet» / «Todavía no está claro», `yes_no_why`, `advice`, ключевые слова совпадают; сочетания соответствуют значениям карт-пар |
| Запреты сайта | ручной проход по `reader.en.md`, `reader.es.md`, `reader_banned_terms.json` | дат и сроков нет, гарантий и «судьбы» нет, о мыслях и чувствах другого человека утверждений нет, прогнозов здоровья/денег/суда нет, специалистов нет, страха нет |
| Испанский | «tú», родовые формы о читателе, «al derecho» / «al revés», мексиканская лексика | родовых форм о читателе нет; «invertida» только в title и description; испанизмов (Испания) нет; есть кальки с английского — список в разделе 4 |

Чего я не мог проверить: совпадение номеров страниц транскрипции Wikisource с бумажным изданием (сети нет в
задании; см. ответ на сомнение 1 и 5); частотность вопросов FAQ, взятых не из «Похожих вопросов» этой карты.

---

## 1. Общие замечания ко всем четырём страницам

### Critical

**К1. Блок `about_this_page`: «edited by the Arcana Diary editor» / «editado por el equipo editorial de Arcana Diary».**
Страница заявляет человеческую редактуру. По решению владельца тексты проверяет модель, а не человек. Если
человек не читает каждую страницу перед публикацией, это ложное заявление о проверке — ровно то, что
база знаний запрещает (c05.06, правило 2 и «вымышленные авторы», стр. 449–453; c05.04). Кроме того, EN говорит
об одном редакторе («the editor»), ES — о команде («equipo editorial»).
Исправление до решения владельца (вопрос 1): убрать слова о редакторе. Текст:
- EN: «Written with AI. Waite's meanings are taken from his book and quoted with page numbers; modern readings follow Arcana Diary's card meanings. A second AI model checked every quote and page number against the book.»
- ES: «Texto escrito con IA. Los significados de Waite salen de su libro y se citan con número de página; las lecturas modernas siguen los significados de cartas de Arcana Diary. Un segundo modelo de IA revisó cada cita y cada página contra el libro.»

### Important

**О1. Метка «современное чтение» стоит не везде.** Блок `waite` обещает: «This page gives both and says which
is which» / «Aquí verás las dos, bien separadas». Но блоки `work_money`, `advice`, `in_a_reading` (все 4
страницы), `love` (ES El Loco, EN и ES Тройка) и `reversed` (первый абзац) идут без метки. При этом
«In modern readings» повторяется 3 раза на странице — заметный штамп.
Исправление: одна граница вместо многих меток. Последний абзац блока `waite`:
- EN: «Everything below is the modern reading used on Arcana Diary. Where a line comes from Waite, we name him and give the page.»
- ES: «Todo lo que sigue es la lectura moderna que usamos en Arcana Diary. Cuando algo viene de Waite, lo decimos y damos la página.»
После этого «In modern readings» / «En las lecturas modernas» в начале блоков убрать, оставить только там, где
в одном абзаце стоят рядом Уэйт и современное чтение.

**О2. FAQ повторяет блоки страницы.** Шаблон требует: «ответы не повторяют разделы, а отсылают к ним»
(`10-card-serp-study.md`, блок 17). Фактически:
- ES El Loco: 3 вопроса из 5 дословно или почти дословно повторяют H2 («¿Qué significa El Loco en el amor?»,
  «…sí o no?», «…como sentimiento?»), ответы — пересказ тех же блоков с теми же фразами («ligero de equipaje, y
  el camino frente a él está abierto» — дважды; «Habla de tu actitud, no de lo que pasa del otro lado» — дважды).
- ES Tres de Espadas: 4 из 5 вопросов повторяют H2 (amor, consejo, sí o no, qué simbolizan); «tres espadas
  atraviesan el corazón bajo la lluvia y la herida está abierta» — дважды.
- EN: «What is the advice…» в обоих FAQ повторяет блок `advice` (тот же пример с маршрутом / тем же «write it down»).
Причина: в ES заголовки блоков уже вопросы, и FAQ стал их копией. Исправление — в шаблоне (раздел 3, п. 4):
в FAQ только вопросы, на которые нет своего H2; если вопрос из выдачи совпадает с H2 — ответом служит сам блок,
в FAQ он не идёт.

**О3. Одинаковые фразы у двух карт — будущий «шаблонный след» на 78 картах.** Совпадает 9–13 % пятисловных
цепочек между Шутом и Тройкой Мечей (EN 142, ES 171). Дословно одинаковы:
- `in_a_reading`: «describes a role, not a real individual» / «If it stands for you, it points to the part of you that…» /
  «As a feeling about a situation you are in, it names…» / «The card speaks about your side of the situation, not anyone else's.»
- `yes_no`: оба абзаца целиком, кроме причины.
- `combinations`: «These pairs are modern readings, built on our meanings for each card.»
- строка Golden Dawn, `draw_cta`, `about_this_page`, «With money, the card makes no forecast.»
Это риск, о котором предупреждает сам разбор (5.6.3, класс сбоев 3: совпадение шинглов). Исправление: всё, что
одинаково у всех карт, — строка интерфейса в шаблоне этапа 6, а не текст в JSON карты (раздел 3, п. 2).

**О4. Строка Golden Dawn без источника в репозитории.** Обе атрибуции верны по традиции (Шут — Воздух; Тройка
Мечей — Сатурн в Весах), но в `content/sources/` источника нет, а README объявляет Уэйта единственным
источником фактов. Писать 78 атрибуций «по памяти модели» нельзя. Исправление — раздел 3, п. 5 и вопрос 3.

**О5. `about_this_page` и `sources`: неточные диапазоны и нет даты и ссылки.**
- «pp. 29, 152–161» (EN/ES Шут) и «Waite's own description (pp. 152–161)» в `waite.note`: диапазон захватывает
  страницы карты The World (156–159). Верно: «pp. 29–30, 152, 155 и 161».
- «Written with AI from Waite's book» неточно: современные значения взяты не из книги (см. текст в К1).
- «checked by a stronger AI model» / «un modelo de IA más potente» — читателю «более сильная» ничего не говорит;
  писать «a second AI model» и что именно проверено.
- Нет даты проверки и ссылки на общедоступный текст Уэйта, хотя шаблон их требует (блок 19 и таблица пробелов:
  «со ссылкой на общедоступный текст»).
- `about_this_page` дублирует массив `sources` — должен собираться из него, а не писаться руками.

**О6. Архаичные слова Уэйта о психике поданы по-разному и местами неточно.** У Шута «mania, delirium, frenzy»
честно объяснены как «excess». У Тройки пояснение придумано: «in Waite's day "alienation" meant being set apart,
here from your own clear thinking» — на деле «mental alienation» в его время значило помрачение рассудка.
Смягчать можно, но не выдавая смягчение за историческую справку. Это важно для остальных карт: у Уэйта в списках
есть «Death, miscarriage» (Nine of Swords, p. 236), болезни, суды. Нужно одно правило — раздел 3, п. 6 и вопрос 4.

---

## 2. Замечания по страницам

### 2.1. EN — The Fool (`en/major-00-fool.json`)

**Important**
1. `on_the_card`, абз. 3 — номер страницы. «…an animal attacking the Fool from behind… (p. 29)». У Уэйта фраза
   переходит на следующую страницу: «…is [p. 30] attacking him from behind». Исправить: «(pp. 29–30)»; так же в
   `about_this_page` и `sources`.
2. `on_the_card` — нет солнца. На скане оно занимает весь правый верхний угол, и у Уэйта о нём отдельная фраза
   (pp. 152–155). Конкуренты разбирают символы по одному; у нас самый заметный символ пропущен. Добавить во 2-й абзац:
   «A white sun fills the corner behind him; Waite writes that it "knows whence he came, whither he is going" (pp. 152–155).»
   Туда же можно взять сильную дословную фразу, которой нет ни у кого в топе: «His countenance is full of
   intelligence and expectant dream» (p. 152).

**Minor**
3. `capsule`: причина вердикта «because the road is open» взята из испанского `yes_no_why`; английский — «steps
   forward with a light bag and an open face». Привести к своему: «…upright leans yes: he steps forward, ready for what is new.»
4. `work_money`, абз. 2: «Waite's word "extravagance" is the card's own warning here» — Уэйт не связывает слово с
   деньгами. Мягче: «Waite's list has a word for the second case: "extravagance".»
5. `faq` 1 и 2 («positive card?» / «bad card?») отвечают одно и то же («leans yes», «not clear yet», список Уэйта).
   Оставить оба вопроса можно (оба из выдачи), но развести ответы: в первом — что карта поддерживает, во втором —
   только про перевёрнутую и список Уэйта, без повторного «not clear yet».
6. `faq` 4 (advice) повторяет блок `advice` — см. О2.
7. `waite.note` и `about_this_page`: диапазон «152–161» — см. О5.
8. Объём: 1 806 слов при потолке 1 800 (текст без заголовков — 1 685). После правок О2–О3 уйдёт ≈ 150 слов.

Проверено и верно: все 8 цитат («with light step…», «has no terror», «the most speaking of all the symbols»,
«the journey outward», «the spirit in search of experience», «the Zero is an unnumbered card», оба списка
pp. 286–287, «principle, beginning, source» p. 196); «bewrayment» объяснено правильно; ссылка pp. 309–310
(«must be judged by considering the general trend of the cards») передана верно; «Holding back out of doubt is a
modern reading, not Waite's» — честно.

### 2.2. ES — El Loco (`es/major-00-fool.json`)

**Important**
1. `on_the_card`, абз. 3: «(p. 29)» → «(pp. 29–30)» — как в EN.
2. `on_the_card`: нет солнца — как в EN. Текст: «Detrás de él, un sol blanco llena la esquina; Waite escribe que ese sol sabe de dónde viene el joven y a dónde va (pp. 152–155).»
3. `waite`, абз. 1–2: список Уэйта стоит по-английски внутри испанского абзаца, а переведены только 4 слова из 14.
   Читатель из Мексики главного отличия страницы не поймёт. Исправление (если владелец согласен, вопрос 2): после
   цитаты — «(traducción nuestra: insensatez, manía, exceso, embriaguez, delirio, frenesí, delatarse; al revés:
   negligencia, ausencia, dispersión, descuido, apatía, nulidad, vanidad)».
4. `waite`, абз. 2 и `work_money`, абз. 2: «extravagancia» / «La «extravagance» de Waite» — ложный друг переводчика:
   по-испански «extravagancia» — чудачество, а не излишество. Исправить: «exceso»; в `work_money`:
   «Waite ya lo advertía con una palabra de su lista: «extravagance», el exceso.»
5. `waite`, абз. 3: «La llamó el más elocuente de todos los símbolos, el viaje hacia afuera» — Уэйт не «называл»
   карту путешествием, он писал, что Шут его «означает» («He signifies the journey outward», p. 161). Исправить:
   «Lo llamó el más elocuente de todos los símbolos y escribió que representa el viaje hacia afuera (p. 161); del
   joven dice que es el espíritu en busca de experiencia (p. 155).»
6. `faq`: 3 из 5 вопросов дублируют H2 — см. О2. Оставить «¿Qué significa si te sale El Loco…?» и «¿Qué número
   es…?»; добавить вопрос, которого на странице нет, а в шаблоне он главный: «¿El Loco es una carta buena o mala?».

**Minor**
7. `description`: «El Loco al derecho e invertida» — мужское имя карты и женское «invertida» (в правилах чтеца это
   прямо названо ошибкой). Исправить: «Qué significa El Loco al derecho y al revés (carta invertida): amor, trabajo
   y consejo. Palabras de Waite (1911), la carta de 1909 y si es sí o no.» (≈ 150 знаков; «Sácala para tu pregunta»
   оставить, если влезает в 160).
8. Ключевое слово «espontaneidad» есть в таблице, но в тексте страницы не встречается ни разу; капсула вместо него
   говорит «ligereza». Вставить слово в `upright` или в капсулу.
9. `love`: нет метки современного чтения (в EN есть) — закрывается правкой О1.
10. «orilla» о краю обрыва — 5 раз, «borde» — 1; в `meanings.es.json` — «borde de un precipicio». Привести к «borde».
11. Кальки и неловкие фразы — в таблице раздела 4.
12. `not_to_confuse`: «un bastón firme» — у Уэйта «stout» (толстый): «un bastón grueso».
13. Объём: 1 856 слов (текст — 1 715) при потолке 1 800.

### 2.3. EN — Three of Swords (`en/swords-03-three.json`)

**Important**
1. `waite`, абз. 2: выдуманная справка о слове «alienation» — см. О6. Исправить: «The reversed list turns inward,
   toward a mind pulled off its course. "Mental alienation" is a harsh phrase of Waite's time; we do not read the
   card as a statement about anyone's mind, only as scattered, restless thoughts.»
2. Ключевое слово «release» (из `meanings.en.json`) стоит в таблице, а в тексте страницы его нет: из блока
   `upright` выпала фраза базы «Let yourself feel it and let the rain fall». Вернуть: «Letting the hurt out is the
   "release" in this card: let the rain fall.» (В ES на этом месте «tristeza» — расхождение EN/ES в базе, не ошибка
   страницы, но стоит знать.)

**Minor**
3. `capsule`: вердикт без причины («upright leans no.»), хотя шаблон требует причину в нескольких словах:
   «…upright leans no: the picture is one of hurt, not ease.»
4. `waite.quote` начинается с рубрики «Divinatory Meanings:» — убрать рубрику, оставить слова Уэйта.
5. `not_to_confuse`: «disappointment, and the moment you begin to see what remains» стоит сразу после «(p. 216)» и
   читается как слова Уэйта. У него близко («something remains over»), но формулировка наша. Развести: «…(p. 216).
   Waite calls it a card of loss where "something remains over"; today it is read as disappointment…»
6. `faq` 3 (advice) повторяет блок `advice` — см. О2.
7. `faq` 4 («how do they see me»): подача верная (см. сомнение 7), но «A card cannot look into another person's
   mind» повторяет строку, которую сайт и так показывает. Короче: «We do not read cards about what another person
   thinks. The Three of Swords can show your side…»
8. Title — ровно 60 знаков, description — ровно 160: на границе. Для карт с длинными именами (Knight of Pentacles,
   The High Priestess) сработает резервная формула — проверить заранее по всем 78.
9. Объём: 1 490 слов при потолке 1 400 (текст — 1 330, в норме).
10. `about_this_page`: «not those of the Spanish or Marseille decks» — в EN-версии «Spanish deck» лишнее (путаница с
    baraja española есть только в мексиканской выдаче).

Проверено и верно: описание и оба списка (p. 248), «too simple and obvious to call for specific enumeration»,
Nine of Swords (p. 236), Five of Cups (p. 216); тяжёлые слова Уэйта у Девятки («Death… miscarriage») на страницу не
попали — правильно.

### 2.4. ES — Tres de Espadas (`es/swords-03-three.json`)

**Important**
1. `waite`, абз. 2: «(«alienation» era quedar apartado, aquí de tu propia claridad)» — та же выдуманная справка,
   см. О6. Исправить: «La segunda mira hacia adentro, a una mente que pierde el rumbo. «Mental alienation» es una
   expresión dura de la época de Waite; aquí no la leemos como algo sobre la mente de nadie, solo como
   pensamientos dispersos.»
2. `waite`: оба списка по-английски без перевода — как у El Loco. Добавить «(traducción nuestra: alejamiento,
   ausencia, demora, división, ruptura, dispersión; al revés: enajenación, error, pérdida, distracción, desorden,
   confusión)» — при согласии владельца (вопрос 2).
3. `faq`: 4 из 5 вопросов дублируют H2 — см. О2. Оставить «¿Qué significa el Tres de Espadas en el tarot?»;
   добавить «¿El Tres de Espadas siempre significa ruptura?» и «¿Es una carta mala?» (в EN-версии оба есть).
4. Четыре H2 без имени карты: «¿Qué significa en el trabajo y el dinero?», «¿Qué significa como persona y como
   sentimiento?», «¿Qué significa junto a otras cartas?», «¿Cómo distinguirla del…?». У El Loco имя есть везде.
   Заголовок должен читаться отдельно от страницы (c03.03; извлечение фрагментов). Добавить «el Tres de Espadas».

**Minor**
5. `on_the_card`, заголовок «¿Qué simbolizan las tres espadas de la carta?» — блок описывает весь рисунок, а
   шаблон у El Loco другой («¿Qué hay en la carta de…?»). Единый вариант: «¿Qué hay en la carta del Tres de Espadas
   y qué simbolizan las espadas?»
6. `on_the_card`, абз. 2: «una espada baja recta por el centro y dos lo cruzan» — «lo» относится к «centro».
   Исправить: «una espada baja recta por el centro del corazón y las otras dos lo cruzan en diagonal».
7. `description`: «el Tres de Espadas al derecho e invertida» — то же несогласование, что у El Loco.
8. `capsule`: вердикт без причины: «…al derecho es no: la herida está abierta.»
9. `waite.quote` — убрать рубрику «Divinatory Meanings:».
10. Кальки — в таблице раздела 4.
11. Объём: 1 567 слов (текст — 1 415) при потолке 1 400 — выше нормы даже без заголовков; уйдёт после правки FAQ.

---

## 3. Изменения шаблона для всех 78 карт

1. **Одна граница «Уэйт / современное»** в конце блока `waite` (текст в О1) вместо метки в каждом блоке. Дальше имя
   Уэйта и страница — только там, где это действительно он.
2. **Общие фразы — в шаблон вёрстки, не в JSON карты.** Строками интерфейса становятся: правило «да/нет» (оба
   абзаца, кроме причины из `yes_no_why`), вводная к сочетаниям, оговорки «роль, а не реальный человек» и «карта
   говорит о твоей стороне», «о деньгах прогноза нет», CTA, блок «About this page» (собирается из `sources`).
   В JSON карты остаётся только то, что у этой карты своё. Блок `in_a_reading` писать без каркаса «As a person… /
   As a feeling…» — каждый раз своей фразой.
3. **Проверка совпадений между картами перед выпуском каждой партии:** доля общих пятисловных цепочек между любыми
   двумя страницами одного языка — не выше 3 % после вынесения общих строк (сейчас 9–13 %).
4. **FAQ не повторяет H2.** В FAQ идут только вопросы, у которых нет своего блока. Обязательный вопрос в обоих
   языках — «хорошая или плохая карта?» (главная неопределённость читателя по шаблону; в ES-образцах его нет).
   Ответ FAQ — новая мысль или ссылка на блок, без фраз из блока.
5. **Golden Dawn — из таблицы данных, не из текста модели.** Положить в `content/sources/` общедоступный источник
   (Book T) и собрать `correspondences.json` на 78 карт; строку показывать в «строке фактов» под H1 (блок 1 шаблона),
   а не абзацем в описании рисунка. До появления источника строку не публиковать. Фразу «Waite does not use this
   attribution» можно подкрепить его же словами: «nearly every attribution is wrong» (p. 161).
6. **Правило для тяжёлых слов Уэйта** (смерть, болезнь, беременность, суд, помрачение ума). Цитату даём дословно, но
   в поле `quote` выбираем фрагмент ≤ 25 слов без таких слов, когда это возможно; когда невозможно — рядом стоит
   строка шаблона «исторический список; на Arcana Diary эти слова не читаются как прогноз». Никаких придуманных
   этимологий и смягчающих «переводов смысла».
7. **Номера страниц:** если фраза переходит со страницы на страницу — указывать обе; диапазон — только когда весь
   диапазон про эту карту. Автор текста обязан выписать для проверяющего строку источника с меткой `[p. N]` для
   каждой ссылки.
8. **Детали «по карте 1909» — только после просмотра скана** из `site/public/cards/`, всегда с оборотом «On the
   1909 card…» / «En la carta de 1909…». По памяти нельзя: в поздних тиражах цвета другие. Описание должно
   называть самый крупный видимый символ (у Шута пропущено солнце).
9. **Испанская цитата:** английский оригинал в `quote` + перевод всего списка с пометкой «traducción nuestra»; в
   вёрстке английскому фрагменту ставить `lang="en"`. Отдельный список «ложных друзей» для автора (extravagance,
   alienation, distribution, absence, principle).
10. **Каждое ключевое слово из таблицы должно встретиться в тексте** своего языка хотя бы раз (сейчас нет
    «release» в EN Тройке и «espontaneidad» в ES Шуте).
11. **Капсула:** четвёртое предложение всегда с причиной вердикта из `yes_no_why` своего языка.
12. **Заголовки:** каждый H2 содержит имя карты (в обоих языках); в ES описание рисунка всегда «¿Qué hay en la carta
    de…?». ES title/description: не ставить «invertida» после имени карты; формула description — «al derecho y al
    revés (carta invertida)».
13. **Новые поля схемы:** `reviewed_at` (дата проверки), `sources[].url` (ссылка на Wikisource для Уэйта и на
    Wikimedia Commons для скана), `facts` (аркан, номер / масть и ранг, соответствие) — блок 1 шаблона сейчас в JSON
    не представлен. Упоминания других карт в тексте (Six of Swords, Nine of Swords, Five of Cups) должны
    становиться ссылками — нужен список `mentions` или автоссылки на этапе 6; в `related` их нет.
14. **Объём считать по тексту без заголовков и вопросов FAQ** и держать с запасом: старшие ≤ 1 650, младшие
    ≤ 1 300 слов текста. Блок «как итог» из шаблона (блок 12) не возвращать — автор убрал его правильно: это прогноз.
15. **Блок символов:** там, где у Уэйта есть слова о символе, давать их (солнце, сумка, роза); современные
    значения символов — только если они есть в базе проекта, иначе не писать (не из памяти модели).

---

## 4. Оценка по вопросам задания

### Получит ли читатель полный и надёжный ответ быстрее, чем у конкурентов

Да, по сути — быстрее и честнее: капсула в 51–59 слов сразу отвечает «что значит / перевёрнутая / хорошая или
плохая / да или нет»; у Biddy Tarot и Labyrinthos до ответа нужно дочитать описание рисунка. Дословный Уэйт со
страницей, скан 1909, открытое правило «да/нет» и блок «не перепутать» — этого в топе нет.

Слабее, чем у топа:
- **Символы.** Топ объясняет каждый символ (роза, собака, солнце, горы). У нас Шут — перечень предметов почти без
  смысла, солнце пропущено. Усилить словами Уэйта (правка 2.1.2), а не общими «роза — чистота».
- **Испанская версия прячет главное отличие:** цитата Уэйта по-английски без перевода.
- **«Хорошая или плохая?»** в ES нет отдельным вопросом (только в капсуле), хотя это вопрос № 1.
- **Место Шута в колоде** (0, 21 или 22) — в EN только вскользь в FAQ «strongest»; в ES есть хороший отдельный ответ.
  Перенести его и в EN вместо одного из двух вопросов «positive / bad».
- **Нет даты и ссылки на первоисточник** — доверие заявлено, но не проверяемо в один клик.

### Отличимо ли от массового ИИ-текста

Внутри одной страницы — да: конкретные детали скана, цитаты со страницами, честные «это не Уэйт», нет вступлений и
выводов, нет опыта от первого лица, нет выдуманных авторов. Удачные места: «Waite lists what happens, and the
picture shows how it feels»; «No hay personas ni paisaje: solo el corazón, las espadas y el mal tiempo»; вопрос
«Is there energy for this? Look to the Ace».
Между страницами — пока нет: одинаковые каркасы блоков `yes_no`, `in_a_reading`, `combinations`, FAQ-пересказы
(О2, О3). На двух картах это терпимо, на 78 даст типовой след. Лечится пунктами 2–4 раздела 3.

### Испанский: естественность

В целом это мексиканский испанский, а не перевод: «se atora», «te hace sentido», «sin planearlo de más», «pegaron
fuerte», «tragarte lo que sientes», «tu gente», «¿Me animo a lo desconocido?». Обращение на «tú», родовых форм о
читателе нет, слов из Испании нет. Кальки с английского и неловкие места:

| Страница, блок | Как написано | Как лучше |
|---|---|---|
| El Loco, `ask_yourself` | «¿Qué paso nuevo llevo tiempo rodeando…?» | «¿A qué paso nuevo le llevo rato dando vueltas, y cuál sería su versión más pequeña?» |
| El Loco, `ask_yourself` | «¿Qué cargo que podría dejar antes de empezar?» | «¿Qué vengo cargando que podría soltar antes de empezar?» |
| El Loco, `ask_yourself` | «¿Dónde me hace falta más confianza y dónde me hace falta mirar dónde piso?» | «¿En qué necesito confiar más y en qué me conviene fijarme mejor dónde piso?» |
| El Loco, `in_a_reading`, `not_to_confuse`, FAQ | «vértigo en la orilla», «el riesgo de la orilla», «como en la orilla antes de dar el paso» | «vértigo al borde del precipicio», «el riesgo del borde», «como al borde, antes de dar el paso» |
| El Loco, `work_money` | «las prisas por saltar» | «la prisa por saltar» |
| El Loco, `work_money` | «La «extravagance» de Waite es la advertencia de la propia carta» | «Waite ya lo advertía con una palabra de su lista: «extravagance», el exceso.» |
| El Loco и Tres, `in_a_reading` | «la parte tuya que…» | «esa parte de ti que…» |
| El Loco, `not_to_confuse` | «un bastón firme» | «un bastón grueso» |
| обе, `about_this_page` | «lo citamos en inglés original», «citado en inglés original» | «lo citamos en el inglés original» |
| Tres, `about_this_page` | «Son significados Rider-Waite-Smith» | «Son los significados de la baraja Rider-Waite-Smith» |
| Tres, `waite` | «Dicho en sencillo» | «Dicho en palabras sencillas» |
| Tres, `reversed` | «escríbelo y déjalo descansar» | «o escríbelo para sacarlo de la cabeza» |
| Tres, `in_a_reading` | «el ardor de unas palabras que dolieron» | «lo que todavía arde después de unas palabras que dolieron» |
| Tres, `in_a_reading` | «Al revés, puede estar aflojando o quedarse guardado, dando vueltas.» | «Al revés, ese dolor puede estar aflojando, o quedarse guardado y dando vueltas.» |
| Tres, `combinations` | «un traslado lento hacia aguas más tranquilas» | «un avance lento hacia aguas más tranquilas» |
| обе, `description` | «al derecho e invertida» | «al derecho y al revés (carta invertida)» |

---

## 5. Ответы на сомнения автора

1. **Страница Тройки Мечей — p. 248 или 249.** Оставить **248**. Метка `[p. N]` стоит перед текстом страницы: это видно
   по Шуту (метка 152 → заголовок «ZERO / The Fool», 153 пустая, 155 — продолжение фразы) и по всей части III
   (текст на чётных страницах, пустые нечётные — листы с рисунком). По той же логике верны p. 152, 155, 161, 196,
   216, 236, 286–287, 309–310. Одна поправка: нападение животного — pp. 29–30. Сверить 2–3 страницы со сканом
   Wikisource один раз всё же стоит (это проверка транскрипции, а не образцов) — я этого сделать не мог.
2. **Цитата в ES по-английски.** Оставить оригинал в поле `quote` и добавить полный перевод списка с пометкой
   «traducción nuestra». Пересказ без кавычек в абзацах — правильно, так и продолжать. Причины: без перевода
   мексиканский читатель не видит главного отличия страницы; частичный перевод уже дал ошибку («extravagancia»).
3. **Детали по скану 1909.** Оставить. Я сверил оба скана — всё точно. Условия: оборот «On the 1909 card…» в каждом
   таком предложении и обязательный просмотр скана автором и проверяющим для каждой из 76 карт.
4. **Golden Dawn.** Атрибуции в образцах верны, но публиковать строку без источника в репозитории нельзя. Добавить
   Book T в `content/sources/`, собрать таблицу на 78 карт и показывать из данных (раздел 3, п. 5). Если это
   задерживает запуск — выпустить без строки и добавить позже.
5. **Издание.** На странице писать «(1911)» — так книга значится в библиографиях и на титуле. В `sources` добавить,
   по какому тексту идут номера страниц: «page numbers follow the Rider edition as transcribed on Wikisource» со
   ссылкой. Формулировку README («первое издание 1910») стоит перепроверить по странице индекса Wikisource: в 1910
   вышла книга без картинок «The Key to the Tarot», иллюстрированная «Pictorial Key» — в 1911. Утверждаю по памяти,
   не по источнику из репозитория.
6. **Редактор.** Пока человек не читает страницу — слов «edited by» быть не должно (К1). Имя ставить только того,
   кто реально читает каждую страницу перед публикацией. Это вопрос 1 владельцу.
7. **Вопросы FAQ не из выдачи этой карты.** Брать их можно — это настоящие вопросы читателей, — но не тогда, когда
   такой вопрос уже стоит заголовком блока. «Como sentimiento», «sí o no», «en el amor» у нас уже H2, значит в FAQ
   им не место; «¿Qué número es El Loco?» — хороший, оставить. «How do they see me»: подача правильная — отказ
   гадать о другом человеке и разворот к своей стороне, ровно как в правилах чтеца; оставить, сократив первую
   фразу (2.3.7).
8. **Вычитка носителем.** По двум образцам нужды в сплошной вычитке не вижу: ошибок рода, «usted» и испанизмов нет,
   найденное — кальки с английского (таблица в разделе 4). Достаточно выборочной вычитки носителем 8–10 страниц из
   первой партии; решать владельцу (вопрос 5).

---

## 6. Вопросы владельцу

1. **Кто «редактор» на страницах карт?** Будет ли человек (вы) читать каждую страницу перед публикацией? Если да —
   ставим имя. Если нет — пишем только «написано с ИИ, цитаты и страницы проверены второй моделью ИИ», без слова
   «редактор».
2. **Слова Уэйта в испанской версии:** показываем английский оригинал и рядом наш перевод с пометкой «перевод наш»
   (советую) — или оставляем только английский с пересказом?
3. **Строка Golden Dawn:** добавляем в проект источник (Book T) и таблицу соответствий на все 78 карт сейчас — или
   запускаем страницы без этой строки и возвращаемся к ней позже?
4. **Тяжёлые старинные слова Уэйта.** В его списках у ряда карт есть «смерть», «выкидыш», «болезнь», «тяжба»,
   «помрачение ума». Показываем их дословно как исторический текст с оговоркой «мы так не читаем» — или для цитаты
   всегда выбираем кусок без таких слов, даже если он получится неполным?
5. **Вычитка испанского носителем:** достаточно ли выборочной проверки 8–10 страниц живым мексиканцем, или вы
   полагаетесь только на проверку моделью?
