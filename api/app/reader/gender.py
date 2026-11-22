"""Gendered forms about the reader in a Spanish answer (stage 4.7, spec 2026-11-22). Precision first: a missed form
costs nothing (the text stays as the model wrote it), a false hit costs a model call and risks a good text.

A hit is anchored to the second person, so the gender of a card, a thing or another person never counts
(«la carta está invertida», «él está cansado», «la Reina se ve tranquila», «el camino está abierto»):

- a tú verb or a tú clitic — estás, eres, te sientes, te ves, te notas, te quedas, sigues, seas, estés, sentirte,
  quedarte, verte… and «te deja / te tiene / te tengan / te mantiene» (the adjective agrees with te) — then, after
  at most three intensifiers (muy, más, tan, demasiado, un poco, todavía…), an adjective or participle from GENDERED,
  or any word ending -ado / -ada / -ido / -ida that is not a noun or an adverb from NOT_ADJECTIVES (cada, nada,
  vida, lado, demasiado…). The orientation words (invertida, derecho…) never count: they are about a card;
- the infinitive «estar» counts the same way unless a third-person verb stands right before it («puede estar
  abierta», «trata de estar tranquilo») or its clause names someone else (él, ella, tu pareja, la carta…);
- «sola» always; «solo» only where it is the adjective: after más / muy / demasiado / bastante, or before a
  pause, «y», «o» or «en esto» («no estás solo.»; not «estás solo a un paso», where it means "only");
- «ti mismo / ti misma» (a ti, de ti, para ti…), «contigo mismo / misma», «tú mismo / misma» (with the accent:
  «tu mismo camino» is "your same path");
- doublets on one stem: «tranquila o tranquilo», «-o/a», «-a/o», «-o(a)», «-os/as».

find_reader_gender() returns the matched phrases in text order, each once.
"""
import re

# Second-person forms of the verbs that take a predicate adjective about the subject. "estás" etc. need the accent:
# «estas» is "these".
_VERBS = (
    r"estás|estabas|estuviste|estarás|estarías|estés|estuvieras|"
    r"eres|fuiste|serás|serías|seas|fueras|"  # not «eras»: also "eras, ages"
    r"has\s+estado|has\s+sido|habías\s+estado|habías\s+sido|"
    r"te\s+(?:sientes|sentías|sentiste|sentirás|sentirías|sientas|sintieras|"
    r"ves|veías|verás|verías|veas|"
    r"notas|notes|quedas|quedes|quedaste|quedarás|pones|pongas|pusiste|vuelves|vuelvas|"
    r"encuentras|encuentres|mantienes|mantengas|"
    r"has\s+(?:sentido|visto|quedado|vuelto|puesto|notado|mantenido)|"
    r"deja|dejan|deje|dejen|dejó|tiene|tienen|tenga|tengan|mantiene|mantienen|mantenga|mantengan|"
    r"hace\s+sentir|hacen\s+sentir|haga\s+sentir|hagan\s+sentir)|"
    r"sigues|sigas|seguirás|andas|anduviste|vives|"
    r"sentirte|verte|notarte|quedarte|ponerte|volverte|mantenerte|mostrarte|encontrarte|"
    r"sintiéndote|viéndote|quedándote|"
    r"quédate|mantente|siéntete|ponte|vuélvete|muéstrate"
)
# «te deja / te tiene / te mantiene …»: the adjective may belong to a noun after it («te deja lleno el corazón»)
_OBJECT_ANCHOR = re.compile(r"te\s+(?:dej|tien|teng|mant)", re.IGNORECASE)
# Between the verb and the adjective: intensifiers, time words, «siendo» and -mente adverbs ("más solo",
# "un poco perdida", "siendo demasiado duro", "profundamente cansada").
_GAP = (r"(?:(?:muy|más|menos|tan|demasiado|bastante|algo|un\s+poco|un\s+tanto|medio|todavía|aún|ya|ahora|"
        r"siempre|también|tampoco|bien|súper|super|cada\s+vez\s+más|siendo|\w{3,}mente)\s+){0,3}")

# Adjectives and participles with an -o / -a ending that are often said about a person.
GENDERED = (
    "abatido abierto agotado agradecido aislado ansioso apagado apresurado asustado atado atento atorado atrapado "
    "bloqueado bueno callado cansado celoso centrado cerrado ciego claro cómodo comprometido confiado confundido "
    "contento convencido decidido dedicado desanimado descansado desesperado despierto digno dispuesto distinto "
    "distraído dividido dormido dueño duro emocionado enamorado encerrado enfermo enojado entusiasmado equivocado "
    "estancado exhausto expuesto frustrado generoso harto herido honesto ilusionado incómodo inquieto inseguro "
    "listo lleno malo metido molesto motivado nervioso nuevo obligado ocupado orgulloso perdido perfecto pleno "
    "preocupado preparado presionado propenso quieto rebasado receptivo relajado rodeado roto sano satisfecho "
    "seguro sereno severo sincero solito tenso tranquilito tranquilo vacío valioso vendado visto vivo"
).split()
# A tú anchor takes the singular only: «te deja nuevas preguntas», «vives nuevas experiencias» are about things.
_GENDERED_FORMS = sorted({w[:-1] + end for w in GENDERED for end in ("o", "a")}, key=len, reverse=True)
# These often stand before a noun («eres buena persona», «te deja mala espina»): they count only when a pause, the
# end or one of AFTER_ADJECTIVE follows. After «te deja / te tiene» every adjective is held to that rule.
BEFORE_NOUN = {w[:-1] + e for w in "bueno malo nuevo distinto duro valioso pleno lleno abierto claro digno".split()
               for e in ("o", "a")}
AFTER_ADJECTIVE = set("y o e ni pero con contigo en de del para por a al que cuando si como sin ante frente hoy "
                      "ahora ya aquí desde hasta porque pues mientras aunque tras sobre entre más menos también "
                      "todavía aún siempre nunca".split())
# After «te tiene / te tenga…» the participle agrees with the thing kept: «lo que la vida te tiene preparado».
NOT_AFTER_TIENE = {w[:-1] + e for w in "preparado reservado guardado destinado claro".split() for e in ("o", "a")}
# Words ending -ado/-ada/-ido/-ida that are nouns, adverbs or quantifiers, never a predicate about the reader.
NOT_ADJECTIVES = set(
    "cada nada demasiado demasiada vida salida entrada mirada llegada partida medida jornada temporada comida "
    "bebida parada idea lado pasado estado mercado grado prado dado marido partido contenido sonido ruido olvido "
    "nido apellido vestido sentido helado"
    .split()
)
# The orientation of a card: «la carta, invertida», never the reader.
ORIENTATION = {"invertido", "invertida", "derecho", "derecha", "volteado", "volteada"}

_ADJ_LIST = "|".join(_GENDERED_FORMS)
_PARTICIPLE = r"\w{2,}(?:ado|ada|ido|ida|ído|ída)"
_PREDICATE = rf"(?P<adj>{_ADJ_LIST}|{_PARTICIPLE}|solo|sola)(?!\w)"
_ANCHORED = re.compile(rf"(?<!\w)(?P<verb>{_VERBS})\s+(?P<gap>{_GAP}){_PREDICATE}", re.IGNORECASE)
# The infinitives: «estar» with any predicate, «ser» with the curated list only («puede ser dicho» is a passive).
_ESTAR_RX = re.compile(rf"(?<!\w)(?P<verb>estar)\s+(?P<gap>{_GAP}){_PREDICATE}", re.IGNORECASE)
_SER_RX = re.compile(rf"(?<!\w)(?P<verb>ser)\s+(?P<gap>{_GAP})(?P<adj>{_ADJ_LIST}|sola)(?!\w)", re.IGNORECASE)
_MISMO = re.compile(r"(?<!\w)(?:ti|contigo|tú)\s+mism[oa]s?(?!\w)", re.IGNORECASE)
_DOUBLET = re.compile(r"(?<!\w)(?P<stem>\w{3,}?)(?P<a>[oa])(?P<s>s?)\s+o\s+(?P=stem)(?P<b>[oa])(?P=s)(?!\w)",
                      re.IGNORECASE)
_SLASH = re.compile(r"(?<!\w)\w{2,}(?:o/a|a/o|os/as|as/os|o\s?\(a\)|a\s?\(o\)|os\s?\(as\))(?!\w)", re.IGNORECASE)
# A doublet about another person: «un amigo o amiga», «tu hijo o hija», «alguien cercano o cercana».
_PERSON_STEMS = ("amig", "hij", "compañer", "novi", "espos", "herman", "jef", "vecin", "niñ", "maestr", "abuel",
                 "prim", "sobrin", "cuñad", "suegr", "niet", "chic", "muchach", "ti", "doctor")
_OTHER_BEFORE_DOUBLET = set("un una unos unas algún alguna alguien tu tus su sus mi mis el la los las otro otra "
                            "cada ningún ninguna".split())

# «solo» is the adjective only after these, or before a pause / «y» / «o» / «en esto».
_SOLO_BEFORE = {"más", "muy", "demasiado", "bastante"}
_SOLO_AFTER = re.compile(r"\s*(?:[.,;:!?)»…—–]|$|y\b|o\b|en\s+esto\b|frente\b|ante\b)", re.IGNORECASE)
_PAUSE_AFTER = re.compile(r"\s*(?:[.,;:!?)»…—–]|$)")
_NEXT_WORD = re.compile(r"\s+(\w+)")
# A third-person verb among the three words before «estar» / «ser»: the subject is someone or something else.
_THIRD_BEFORE_ESTAR = set(
    "puede pueden podría podrían pudo debe deben debería deberían suele suelen parece parecen quiere quieren "
    "necesita necesitan merece merecen intenta intentan prefiere prefieren logra logran busca buscan decide "
    "deciden sabe saben va van vuelve vuelven trata tratan deja dejan dejó acaba acaban empieza empiezan "
    "termina terminan tiene tienen hay sigue siguen elige eligen pide piden acepta aceptan aprende aprenden "
    "representa representan muestra muestran espera esperan teme temen"
    .split()
)
# Someone or something else named in the clause before «estar» / «ser».
_OTHER_SUBJECT = re.compile(
    r"(?<!\w)(?:él|ella|ellos|ellas|usted|ustedes|tu\s+pareja|tu\s+ex|esa\s+persona|la\s+otra\s+persona|"
    r"otra\s+persona|alguien|carta|cartas|arcano|arcanos)(?!\w)", re.IGNORECASE)
_LINKS_BEFORE_INFINITIVE = set("y o e ni de a para sin que por al".split())
_CLAUSE_END = re.compile(r"[.,!?;:—–\n]|(?<!\w)(?:pero|aunque|mientras)(?!\w)", re.IGNORECASE)
_WORD = re.compile(r"\w+")
_ONDA = re.compile(r"\s+onda(?!\w)", re.IGNORECASE)


def _followed_by_pause_or_link(text: str, end: int) -> bool:
    """A pause or the end, or a small linking word: the adjective does not stand before a noun."""
    if _PAUSE_AFTER.match(text, end):
        return True
    nxt = _NEXT_WORD.match(text, end)
    if not nxt:
        return False
    word = nxt.group(1).lower()
    return word in AFTER_ADJECTIVE or word.endswith(("ando", "endo"))


def _predicate_ok(text: str, m: re.Match) -> bool:
    adj = m.group("adj").lower()
    if adj in NOT_ADJECTIVES or adj in ORIENTATION:
        return False
    if adj in ("bueno", "buena") and _ONDA.match(text, m.end()):
        return False  # «eres buena onda» is said of anyone
    if adj == "solo":
        gap = m.group("gap").split()
        before = gap[-1].lower() if gap else ""
        return before in _SOLO_BEFORE or bool(_SOLO_AFTER.match(text, m.end()))
    verb = m.group("verb")
    if _OBJECT_ANCHOR.match(verb):
        if re.match(r"te\s+t", verb, re.IGNORECASE) and adj in NOT_AFTER_TIENE:
            return False
        if adj in ("claro", "clara"):
            return False  # «te deja claro que…»
        return _followed_by_pause_or_link(text, m.end())
    if adj in BEFORE_NOUN:
        return _followed_by_pause_or_link(text, m.end())
    return True


def _clause_before(text: str, start: int) -> str:
    begin = 0
    for end in _CLAUSE_END.finditer(text, 0, start):
        begin = end.end()
    return text[begin:start]


def _infinitive_ok(text: str, m: re.Match) -> bool:
    """«estar» / «ser»: not when a third-person verb or «tu <noun> <verb>» stands right before it, nor when its
    clause names someone or something else."""
    clause = _clause_before(text, m.start())
    words = [w.lower() for w in _WORD.findall(clause)]
    if any(w in _THIRD_BEFORE_ESTAR for w in words[-3:]):
        return False
    if len(words) >= 3 and words[-3] in ("tu", "tus") and words[-1] not in _LINKS_BEFORE_INFINITIVE:
        return False  # «tu corazón quisiera estar tranquilo»; not «cuidar tu ánimo y ser claro»
    return not _OTHER_SUBJECT.search(clause)


def _doublet_ok(text: str, m: re.Match) -> bool:
    if m.group("a").lower() == m.group("b").lower():
        return False
    if m.group("stem").lower().startswith(_PERSON_STEMS):
        return False
    before = [w.lower() for w in _WORD.findall(text[max(0, m.start() - 40):m.start()])]
    return not (before and before[-1] in _OTHER_BEFORE_DOUBLET)


def find_reader_gender(text: str) -> list[str]:
    """The phrases that speak of the reader with a gendered form, in text order, each once ([] for none)."""
    if not text:
        return []
    found: list[tuple[int, str]] = []
    for m in _ANCHORED.finditer(text):
        if _predicate_ok(text, m):
            found.append((m.start(), m.group(0)))
    for rx in (_ESTAR_RX, _SER_RX):
        for m in rx.finditer(text):
            if _predicate_ok(text, m) and _infinitive_ok(text, m):
                found.append((m.start(), m.group(0)))
    found += [(m.start(), m.group(0)) for m in _MISMO.finditer(text)]
    found += [(m.start(), m.group(0)) for m in _DOUBLET.finditer(text) if _doublet_ok(text, m)]
    found += [(m.start(), m.group(0)) for m in _SLASH.finditer(text)]
    out: list[str] = []
    for _, phrase in sorted(found):
        phrase = " ".join(phrase.split())
        if phrase not in out:
            out.append(phrase)
    return out
