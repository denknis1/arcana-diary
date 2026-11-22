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
    r"te\s+(?:sientes|sentías|sentiste|sentirás|sentirías|sientas|sintieras|"
    r"ves|veías|verás|verías|veas|"
    r"notas|notes|quedas|quedes|quedaste|quedarás|pones|pongas|pusiste|vuelves|vuelvas|"
    r"encuentras|encuentres|mantienes|mantengas|"
    r"deja|dejan|deje|dejen|dejó|tiene|tienen|tenga|tengan|mantiene|mantienen|mantenga|mantengan|"
    r"hace\s+sentir|hacen\s+sentir|haga\s+sentir|hagan\s+sentir)|"
    r"sigues|sigas|seguirás|andas|anduviste|vives|"
    r"sentirte|verte|notarte|quedarte|ponerte|volverte|mantenerte|mostrarte|encontrarte|"
    r"sintiéndote|viéndote|quedándote"
)
_ESTAR = r"estar"
# Between the verb and the adjective: intensifiers and time words only ("más solo", "un poco perdida").
_GAP = (r"(?:(?:muy|más|menos|tan|demasiado|bastante|algo|un\s+poco|un\s+tanto|medio|todavía|aún|ya|ahora|"
        r"siempre|también|tampoco|realmente|bien|súper|super|cada\s+vez\s+más)\s+){0,3}")

# Adjectives and participles with an -o / -a ending that are often said about a person.
GENDERED = (
    "abatido agotado agradecido aislado ansioso apagado apresurado asustado atado atento atorado atrapado "
    "bloqueado bueno callado cansado celoso centrado cerrado cómodo comprometido confiado confundido contento "
    "convencido decidido dedicado desanimado descansado desesperado despierto dispuesto distinto dividido dormido "
    "dueño duro emocionado enamorado encerrado enojado entusiasmado equivocado estancado exhausto expuesto "
    "frustrado harto herido honesto ilusionado incómodo inquieto inseguro listo lleno malo metido molesto "
    "motivado nervioso nuevo obligado ocupado orgulloso perdido pleno preocupado preparado presionado propenso "
    "quieto rebasado receptivo relajado rodeado satisfecho seguro sereno sincero solito tenso tranquilito "
    "tranquilo vacío valioso vendado"
).split()
_GENDERED_FORMS = sorted({w[:-1] + end for w in GENDERED for end in ("o", "a", "os", "as")}, key=len, reverse=True)
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
_PARTICIPLE = r"\w{2,}(?:ado|ada|ido|ida)"
_PREDICATE = rf"(?P<adj>{_ADJ_LIST}|{_PARTICIPLE}|solo|sola|solos|solas)(?!\w)"
_ANCHORED = re.compile(rf"(?<!\w)(?P<verb>{_VERBS})\s+(?P<gap>{_GAP}){_PREDICATE}", re.IGNORECASE)
_ESTAR_RX = re.compile(rf"(?<!\w)(?P<verb>{_ESTAR})\s+(?P<gap>{_GAP}){_PREDICATE}", re.IGNORECASE)
_MISMO = re.compile(r"(?<!\w)(?:ti|contigo|tú)\s+mism[oa]s?(?!\w)", re.IGNORECASE)
_DOUBLET = re.compile(r"(?<!\w)(?P<stem>\w{3,}?)(?P<a>[oa])(?P<s>s?)\s+o\s+(?P=stem)(?P<b>[oa])(?P=s)(?!\w)",
                      re.IGNORECASE)
_SLASH = re.compile(r"(?<!\w)\w{2,}(?:o/a|a/o|os/as|as/os|o\s?\(a\)|a\s?\(o\)|os\s?\(as\))(?!\w)", re.IGNORECASE)

# «solo» is the adjective only after these, or before a pause / «y» / «o» / «en esto».
_SOLO_BEFORE = {"más", "muy", "demasiado", "bastante"}
_SOLO_AFTER = re.compile(r"\s*(?:[.,;:!?)»…—–]|$|y\b|o\b|en\s+esto\b|frente\b|ante\b)", re.IGNORECASE)
# A third-person verb right before «estar»: the subject is someone or something else.
_THIRD_BEFORE_ESTAR = set(
    "puede pueden podría podrían pudo debe deben debería deberían suele suelen parece parecen quiere quieren "
    "necesita necesitan merece merecen intenta intentan prefiere prefieren logra logran busca buscan decide "
    "deciden sabe saben suele va van vuelve vuelven trata tratan deja dejan dejó acaba acaban empieza empiezan "
    "termina terminan tiene tienen hay sigue siguen"
    .split()
)
# Someone or something else named in the clause before «estar».
_OTHER_SUBJECT = re.compile(
    r"(?<!\w)(?:él|ella|ellos|ellas|usted|ustedes|tu\s+pareja|tu\s+ex|esa\s+persona|la\s+otra\s+persona|"
    r"otra\s+persona|alguien|carta|cartas|arcano|arcanos)(?!\w)", re.IGNORECASE)
_CLAUSE_END = re.compile(r"[.,!?;:—–\n]|(?<!\w)(?:pero|aunque|mientras)(?!\w)", re.IGNORECASE)
_WORD = re.compile(r"\w+")
_ONDA = re.compile(r"\s+onda(?!\w)", re.IGNORECASE)


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
    return True


def _clause_before(text: str, start: int) -> str:
    begin = 0
    for end in _CLAUSE_END.finditer(text, 0, start):
        begin = end.end()
    return text[begin:start]


def _estar_ok(text: str, m: re.Match) -> bool:
    clause = _clause_before(text, m.start())
    words = [w.lower() for w in _WORD.findall(clause)]
    if any(w in _THIRD_BEFORE_ESTAR for w in words[-2:]):
        return False
    return not _OTHER_SUBJECT.search(clause)


def _doublet_ok(m: re.Match) -> bool:
    return m.group("a").lower() != m.group("b").lower()


def find_reader_gender(text: str) -> list[str]:
    """The phrases that speak of the reader with a gendered form, in text order, each once ([] for none)."""
    if not text:
        return []
    found: list[tuple[int, str]] = []
    for m in _ANCHORED.finditer(text):
        if _predicate_ok(text, m):
            found.append((m.start(), m.group(0)))
    for m in _ESTAR_RX.finditer(text):
        if _predicate_ok(text, m) and _estar_ok(text, m):
            found.append((m.start(), m.group(0)))
    found += [(m.start(), m.group(0)) for m in _MISMO.finditer(text)]
    found += [(m.start(), m.group(0)) for m in _DOUBLET.finditer(text) if _doublet_ok(m)]
    found += [(m.start(), m.group(0)) for m in _SLASH.finditer(text)]
    out: list[str] = []
    for _, phrase in sorted(found):
        phrase = " ".join(phrase.split())
        if phrase not in out:
            out.append(phrase)
    return out
