import re
from enum import StrEnum

from app.text import GENERIC_DOMAIN_TERMS, normalize, tokenize


class Kind(StrEnum):
    """Cómo trató el servicio la consulta. Es el campo `tipo` de la respuesta."""

    ANSWER = "respuesta"
    OUT_OF_SCOPE = "fuera_de_alcance"
    REFER_TO_DOCTOR = "derivar_medico"
    NO_INFORMATION = "sin_informacion"


MESSAGES = {
    Kind.OUT_OF_SCOPE: (
        "Solo puedo responder consultas sobre estudios genéticos, como el exoma clínico, "
        "el proceso del estudio y las patologías lisosomales. Probá con otra pregunta."
    ),
    Kind.REFER_TO_DOCTOR: (
        "No puedo dar diagnósticos, interpretar resultados de un paciente ni recomendar "
        "tratamientos. Te sugiero hablar de esto con tu médico tratante."
    ),
    Kind.NO_INFORMATION: (
        "No tengo información suficiente para responder eso. "
        "Si es una duda sobre tu caso, consultá a tu médico tratante."
    ),
}

GREETING_MESSAGE = (
    "Hola, soy el asistente del laboratorio de genética. Estoy acá para ayudarte. "
    "¿Qué querés saber?"
)

COURTESY_MESSAGE = "¡De nada! Si te queda alguna duda sobre estudios genéticos, preguntame."

# --- Detección de consultas que piden un diagnóstico, un resultado propio o un tratamiento ---
#
# Todo se aplica sobre el texto sin tildes ni mayúsculas. La idea es separar dos cosas:
#   - una pregunta general ("¿qué síntomas tiene Fabry?", "¿qué es una VUS?"), que se responde;
#   - un caso personal (lo que me pasa, lo que tengo, lo que me salió y qué hacer con eso), que se
#     deriva al médico tratante.
# Los patrones de caso personal exigen un verbo en primera persona o un familiar ("mi hijo"),
# y un término médico a pocas palabras. Así "tiene" en tercera persona no alcanza.

_DISEASES = (
    r"fabry|pompe|gaucher|asmd|mps|mucopolisacaridosis|niemann|enfermedad|enfermedades|"
    r"lisosomal|lisosomales|patologia"
)
_VARIANT_TERMS = r"variantes?|vus|patogenic[ao]s?|benign[ao]s?|mutacion|mutaciones"
_RESULT_TERMS = r"resultados?|informe|positivo|negativo"
_SYMPTOMS = (
    r"dolor|dolores|cansancio|debilidad|mareos?|fiebre|hormigueo|vomitos?|nauseas?|"
    r"falta de aire|ahogo|palpitaciones|calambres?|hinchazon|manchas?|picazon|ardor|"
    r"sintomas?|molestias?"
)
_FAMILY = (
    r"hij[oa]s?|bebes?|nen[ea]s?|mama|papa|madre|padre|espos[oa]|marido|mujer|pareja|"
    r"hermano|hermana|abuel[oa]|ti[oa]|prim[oa]|familiares?|familia"
)
# Hasta tres palabras entre el verbo y el término: "tengo la enfermedad de Fabry" sí,
# "tengo muchas ganas de entender qué es Fabry" no.
_GAP = r"[\s,]+(?:\w+[\s,]+){0,3}?"
_ANY_TERM = rf"\b({_DISEASES}|{_VARIANT_TERMS}|{_RESULT_TERMS}|{_SYMPTOMS})\b"

_REFERRAL_PATTERNS = [
    # Dice que tiene una enfermedad o una variante
    rf"\b(tengo|tenemos|padezco|sufro|me diagnosticaron|me detectaron|me confirmaron|"
    rf"soy portador|soy portadora){_GAP}({_DISEASES}|{_VARIANT_TERMS})\b",
    # Un familiar la tiene
    rf"\b(mi|mis|nuestro|nuestra)\s+({_FAMILY})\b.*?\b(tiene|tienen|tuvo|padece|sufre|siente|"
    rf"presenta|le diagnosticaron|le detectaron|le confirmaron|le salio|le dio|le duele|le duelen)"
    rf"{_GAP}({_DISEASES}|{_VARIANT_TERMS}|{_SYMPTOMS})\b",
    # Cuenta síntomas propios
    rf"\b(tengo|tenemos|siento|sentimos|noto|notamos|presento|sufro|tuve)(?! que\b){_GAP}"
    rf"({_SYMPTOMS})\b",
    r"\bme (duele|duelen|dolia|molesta|molestan|marea|mareo|canso|cansa|agota|hormiguea|"
    r"hormiguean|late|sangra|hincha|hinchan|quema|arde)\b",
    r"\b(estos|mis|mi)\s+sintomas?\b",
    r"\b(estoy|esta|esta mi (hijo|hija))\b.*\b(enfermo|enferma|sano|sana)\b",
    # Pregunta si puede tener o va a tener una enfermedad
    r"\b(puedo|podria|sera que)\b.*\b(tener|padecer)\b",
    r"\bes (hereditario|hereditaria) (en )?(mi|mis)\b",
    # Resultado propio
    r"\b(mi|mis)\b.*\b(resultado|resultados|variante|variantes|informe)\b.*"
    r"\b(significa|quiere decir|indica|es grave|es normal|salio|dio|positivo|negativo)\b",
    # Cualquier mención de tratamiento, general o personal, se deriva al médico
    r"\b(tratamientos?|tratar|tratarse|trata|tratan|curar|curarse|cura|sanar|terapias?|"
    r"medicamentos?|medicacion|remedios?|pastillas?|dosis|drogas?|farmacos?|inyecciones|"
    r"infusiones|reemplazo enzimatico)\b",
    r"\b(debo|tengo que|puedo|deberia)\b.*\b(tomar|tratar|medicar|operar)\b",
    r"\bque (tomo|me tomo|debo tomar|puedo tomar)\b",
    r"\b(me recomienda|me recomiendas|me aconseja|me aconsejas)\b",
    # Cuánto va a vivir alguien: el pronóstico es del médico
    r"\b(pronostico|esperanza de vida|mortal|morir|muere|se muere|cuanto (tiempo )?vive|"
    r"cuanto (tiempo )?(voy a|va a) vivir)\b",
]
_REFERRAL = [re.compile(pattern) for pattern in _REFERRAL_PATTERNS]

# Pedidos de valoración o de consejo sobre algo propio. Solos no alcanzan ("¿qué hago para
# sacar un turno?"): tienen que ir con un término médico. Por eso "me salió una VUS, ¿qué es?"
# es una pregunta general, y "me salió una VUS, ¿es grave?" es un caso personal.
_JUDGMENT_PATTERNS = [
    r"\b(es|sera|seria|esta|estoy)\s+(muy\s+)?(grave|peligros[oa]|malo|mala|preocupante|serio|"
    r"seria|normal)\b",
    r"\bque (hago|debo hacer|tengo que hacer|puedo hacer|me conviene|hacemos)\b",
    r"\b(tengo|debo|tendria)\s+que\s+(preocup\w+|operar\w*|consultar\w*)\b",
    r"\b(me preocupo|preocuparme|preocuparnos)\b",
    r"\b(en mi caso|en nuestro caso|para mi caso)\b",
    r"\bme (afecta|va a afectar|implica)\b",
    r"\b(voy a|va a) (morir|enfermar|empeorar|curar|estar bien)\b",
    r"\b(mis|mi)\s+(hij\w+|nietos?)\b.*\b(heredar\w*|transmit\w+|heredan?)\b",
    r"\b(lo|la) (voy a|puedo|podria) (heredar|transmitir|pasar)\b",
]
_JUDGMENT = [re.compile(pattern) for pattern in _JUDGMENT_PATTERNS]
_ANY_TERM_RE = re.compile(_ANY_TERM)

# Frases que solo anuncian una pregunta ("tengo una duda"): no cuentan como un caso personal.
_PREAMBLE = re.compile(
    r"\b(tengo|tenia|tenemos|me quedo|me quedaron)\s+(una|unas|otra|otras|alguna|algunas|mucha|"
    r"muchas)?\s*(duda|dudas|consulta|consultas|pregunta|preguntas|curiosidad|ganas de saber)\b"
    r"|\b(tengo|tenemos) que (saber|entender|preguntar|consultar)\b"
)

_GREETING = re.compile(r"^\s*(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|hey)\b")
# Palabras que pueden acompañar a un saludo o agradecimiento sin ser una consulta.
_SMALL_TALK = frozenset(
    tokenize(
        "hola buenas buen dias tardes noches hey como estas todo bien tal gracias muchas mil "
        "chau adios hasta luego listo ok dale"
    )
)
_COURTESY = re.compile(r"^\s*(muchas |mil )?(gracias|chau|adios|hasta luego|listo|ok|dale)\b")


def is_greeting(message: str) -> bool:
    """Indica si el mensaje es solo un saludo (sin otra consulta)."""
    text = normalize(message)
    return bool(_GREETING.match(text)) and tokenize(text) <= _SMALL_TALK


def is_courtesy(message: str) -> bool:
    """Indica si el mensaje es solo un agradecimiento o una despedida."""
    text = normalize(message)
    return bool(_COURTESY.match(text)) and tokenize(text) <= _SMALL_TALK


def asks_for_diagnosis(message: str) -> bool:
    """Indica si la consulta pide un diagnóstico, interpretar un resultado o un tratamiento."""
    text = _PREAMBLE.sub(" ", normalize(message))
    if any(pattern.search(text) for pattern in _REFERRAL):
        return True
    return bool(_ANY_TERM_RE.search(text)) and any(p.search(text) for p in _JUDGMENT)


def is_about_genetics(message: str) -> bool:
    """Indica si la consulta menciona algún término del tema, aunque no haya texto para responderla."""
    return bool(tokenize(message) & GENERIC_DOMAIN_TERMS)
