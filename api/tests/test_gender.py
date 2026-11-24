"""Stage 4.7: gendered forms about the reader in Spanish (app/reader/gender.py)."""
import pytest

from app.reader.gender import find_reader_gender

# The forms found in the 4.6 paid run (22.11.2026), in sentences like the ones the reader wrote.
PAID_RUN = [
    ("Es normal que te sientas inquieta con tantas preguntas.", "te sientas inquieta"),
    ("Eres bueno para ver lo que otros necesitan.", "Eres bueno"),
    ("Quizá hoy te sientes más solo de lo que quisieras.", "te sientes más solo"),
    ("Sigues atada a una idea que ya no te sirve.", "Sigues atada"),
    ("No es que estás perdido, es que buscas otra ruta.", "estás perdido"),
    ("Es como estar vendada frente a algo que ya intuyes.", "estar vendada"),
    ("Piensa en lo que esperas de ti misma o de ti.", "ti misma"),
    ("Tal vez eres demasiado duro contigo.", "eres demasiado duro"),
    ("Mira lo que te pides a ti mismo esta semana.", "ti mismo"),
    # the 4.6 run's es-05, missed by the first version of the list
    ("Conviene no forzar decisiones mientras los celos te tengan inquieta.", "te tengan inquieta"),
]

MORE_HITS = [
    ("Hoy estás lista para dar un paso.", "estás lista"),
    ("No estás solo.", "estás solo"),
    ("No estás solo en esto.", "estás solo"),
    ("Estás muy cansada de cargar con todo.", "Estás muy cansada"),
    ("Si te ves rebasado, para un momento.", "te ves rebasado"),
    ("Es un día para sentirte segura de tus pasos.", "sentirte segura"),
    ("No tienes que quedarte callada.", "quedarte callada"),
    ("Esa espera te deja agotada.", "te deja agotada"),
    ("Podrías estar preocupado por nada.", "estar preocupado"),
    ("Sigue así, tranquila o tranquilo, a tu ritmo.", "tranquila o tranquilo"),
    ("Quédate abierta o abierto a lo que venga.", "abierta o abierto"),
    ("Si te sientes cansado/a, descansa.", "cansado/a"),
    ("Cuando estés listo(a), empieza.", "estés listo"),
    ("Cuando estés lista/o, escribe una línea.", "estés lista"),
    ("Habla contigo misma con calma.", "contigo misma"),
    ("Tú mismo sabes lo que pesa.", "Tú mismo"),
    ("Tómate un rato para ti misma o mismo.", "ti misma"),
    ("Eres dueña de tus decisiones.", "Eres dueña"),
    ("Te notas inquieto cuando nadie llama.", "Te notas inquieto"),
    ("Esto te tiene preocupada desde hace días.", "te tiene preocupada"),
    # Fable review I6: misses seen in the saved answers, in the prompt or by hand
    ("Quizá estás siendo demasiado duro contigo.", "estás siendo demasiado duro"),
    ("Te ayuda ser claro contigo sobre lo que quieres.", "ser claro"),
    ("Quizá te ayude cuidar tu ánimo y ser claro con lo que buscas.", "ser claro"),
    ("Lo que necesitas es sentirte visto.", "sentirte visto"),
    ("Vale más moverte que estar perfecto.", "estar perfecto"),
    ("Hoy estás distraída con muchas cosas.", "estás distraída"),
    ("Te sientes atraída por algo nuevo.", "Te sientes atraída"),
    ("Si te sientes caída, descansa.", "te sientes caída"),
    ("Estás abierta a lo que venga.", "Estás abierta"),
    ("Puedes mostrarte abierto.", "mostrarte abierto"),
    ("Has estado muy ocupada estos días.", "Has estado muy ocupada"),
    ("Te has sentido atrapada en lo mismo.", "Te has sentido atrapada"),
    ("Has sido dura contigo.", "Has sido dura"),
    ("Quédate tranquila un momento.", "Quédate tranquila"),
    ("Mantente atento a lo que sientes.", "Mantente atento"),
    ("Estás profundamente cansada.", "Estás profundamente cansada"),
    ("Eres digna de cariño.", "Eres digna"),
    ("Eres generosa con los demás.", "Eres generosa"),
    ("Sientes que estás roto.", "estás roto"),
    ("Te sientes un poco más abierta hoy.", "Te sientes un poco más abierta"),
]

# The six forms that reached the visitor in the paid eval of 24.11.2026 (es-04, fu-es-07, es-37, es-38, es-56,
# fu-es-01), in the sentences the reader wrote, and the shapes around them.
EVAL_20261124 = [
    ("Para abrirte a alguien nuevo, quizá te ayude sentirte acompañado primero.", "sentirte acompañado"),
    ("Lo que sí puedo leer en el Nueve de Bastos es que estás cansada de tanto esfuerzo, o al menos que tu energía "
     "anda corta.", "estás cansada"),
    ("Juntas, las cartas hablan de una espera que pesa y de la necesidad de bajar la presión y ser honesta con tus "
     "propios sentimientos.", "ser honesta"),
    ("Si nada cambia en la forma en que cargas esto, la carta apunta a seguir atrapado entre la presión y la espera.",
     "seguir atrapado"),
    ("Por ahora, el peso está en esperar y revisar qué tan tranquilo estás con la idea.", "tan tranquilo estás"),
    ("El Ocho de Espadas habla de sentirse atado, pero también recuerda que el camino frente a ti está libre.",
     "sentirse atado"),
    # the same shapes, other words
    ("Las cartas invitan a estar atenta a tus propias señales.", "estar atenta"),
    ("La carta habla de ser sincero con tus límites.", "ser sincero"),
    ("La carta sugiere quedarse callado un tiempo.", "quedarse callado"),
    ("Las cartas invitan a continuar abierta al cambio.", "continuar abierta"),
    ("La Torre habla de verse rebasado por todo.", "verse rebasado"),
    ("Lo cansada que estás se nota en cada decisión.", "Lo cansada que estás"),
    ("Mira qué tan seguro te sientes con esto.", "tan seguro te sientes"),
]

# Must not hit: the gender of a card, a thing or another person (the owner's list), then traps that look alike.
OWNER_MISSES = ["La carta está invertida.", "El Emperador, al revés, habla de orden.", "Él está cansado.",
                "Ella está lista.", "La Reina se ve tranquila.", "El camino está abierto."]
TRAPS = [
    "Estás en un momento abierto.",
    "Estás solo a un paso de decidir.",           # «solo» = "only"
    "Eres tan solo una parte de la historia.",    # «tan solo» = "only"
    "Eres buena onda con la gente.",              # said of anyone
    "Sigues cada paso con cuidado.",              # «cada»
    "No estás nada lejos de lograrlo.",           # «nada»
    "Eres demasiado exigente contigo.",           # «demasiado» is an adverb, «exigente» has no gender
    "La puerta puede estar abierta.",
    "Tu pareja puede estar cansada.",
    "Él trata de estar tranquilo.",
    "Ella merece estar tranquila.",
    "La otra persona podría estar confundida.",
    "Además de estar invertida, la carta pide calma.",
    "La carta, invertida, habla de una pausa.",
    "Estas cartas hablan de calma.",              # «estas» = "these"
    "Tu mismo camino te lleva lejos.",            # «tu» without the accent = "your"
    "Tu misma pregunta trae la respuesta.",
    "Habla de la persona misma y de su paso.",    # third person
    "Es la misma carta de ayer.",
    "Te sientes sin energía y está bien.",
    "Estás pasando por un cambio.",
    "Ella se siente sola.",
    "Estás a tiempo de cambiarlo.",
    "Eres capaz de mucho.",
    "Te ves con calma frente a esto.",
    "La Torre está derrumbada.",
    "El Ermitaño está solo en la montaña.",
    "Ellos están juntos desde hace años.",
    "Te toca cuidar tu energía.",
    "Estás más cerca de lo que crees.",
    "Estás del lado de la calma.",
    "Eres parte de algo más grande.",
    "Sigues adelante a tu ritmo.",
    "Puedes escribir y/o dibujar lo que sientes.",
    "Te quedas con lo bueno de este día.",
    "Vives cada día con prisa.",
    "La vida es dura contigo a veces.",
    "Eres tú quien decide.",
    "El Sol está despejado y cálido.",
    "¿Cómo te sientes? Cansada o no, hoy puedes descansar.",  # a pause breaks the anchor
    "El As de Copas, al derecho, habla de cariño.",
    # Fable review I5: confirmed false hits of the first version
    "Esta etapa te deja nuevas preguntas.",
    "Te deja buenos aprendizajes y valiosas lecciones.",
    "Vives nuevas experiencias.",
    "Sigues nuevos caminos.",
    "Sigues distintas rutas.",
    "Te deja mala espina.",
    "Te deja buena impresión.",
    "Te deja lleno el corazón.",
    "Lo que la vida te tiene preparado.",
    "Quizá te tiene reservada una sorpresa.",
    "Esto te deja claro que hay tiempo.",
    "Eres buena persona.",
    "Eres buena gente.",
    "Eres muy buena compañía.",
    "Eres distinta persona cuando descansas.",
    "El Ermitaño elige estar solo.",
    "El Colgado acepta estar atado.",
    "Tu corazón pide estar tranquilo.",
    "Tu cuerpo pide estar descansado.",
    "Tu mente quisiera estar tranquila.",
    "Un amigo o amiga puede ayudarte.",
    "Tu hijo o hija también lo nota.",
    "Habla con alguien cercano o cercana.",
    "Esto puede ser dicho con calma.",
    "No tiene por qué ser perfecto.",
    # stage 4.7 follow-up: the new rules stop at another person, an adverb and a plain infinitive
    "Para él, la carta habla de sentirse atado.",
    "Tu pareja podría ser honesta con tus sentimientos.",
    "Ella tendrá que ser honesta con tus amigos.",
    "Las cartas piden ser honesta con ella.",
    "Las cartas hablan de ser honestos con los demás.",
    "La carta habla de seguir adelante con calma.",
    "La carta sugiere seguir con paciencia y continuar el camino.",
    "El Ermitaño apunta a seguir solo su camino.",
    "La carta invita a sentirse en paz.",
    "La carta invita a quedarse en casa.",
    "La carta habla de sentirse tan bien como sea posible.",
    "Alguien apunta a seguir atrapado.",
    "Tan solo estás empezando.",
    "Qué tan cerca estás de lo que quieres.",
    "Lo importante es que estás aquí.",
    "Lo bueno es que estás aquí.",
    "Lo bueno que tiene esta carta es la calma.",
    "Lo cansado que estaba él.",
    "Más claro que nunca estás en tu camino.",
]


@pytest.mark.parametrize("text, phrase", PAID_RUN + MORE_HITS + EVAL_20261124)
def test_gendered_forms_about_the_reader_hit(text, phrase):
    assert phrase in find_reader_gender(text)


@pytest.mark.parametrize("text", OWNER_MISSES + TRAPS)
def test_other_genders_and_look_alikes_do_not_hit(text):
    assert find_reader_gender(text) == []


def test_the_traps_table_is_broad():
    assert len(TRAPS) >= 20


def test_phrases_come_in_text_order_and_once():
    text = "Estás cansada. Eres buena para escuchar. Estás cansada, sí. Y a ti misma te cuesta."
    assert find_reader_gender(text) == ["Estás cansada", "Eres buena", "ti misma"]


def test_spaces_in_a_phrase_are_normalised_and_empty_text_has_none():
    assert find_reader_gender("Te   sientes\nsola hoy.") == ["Te sientes sola"]
    assert find_reader_gender("") == []


def test_english_has_no_hits():
    assert find_reader_gender("You are tired and lost, and that is fine.") == []
