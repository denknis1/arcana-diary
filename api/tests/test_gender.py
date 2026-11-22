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
]


@pytest.mark.parametrize("text, phrase", PAID_RUN + MORE_HITS)
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
