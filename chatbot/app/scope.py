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

# Consultas que piden un diagnóstico, la lectura de un resultado propio o un tratamiento.
# Se aplican sobre el texto sin tildes ni mayúsculas.
_REFERRAL_PATTERNS = [
    r"\b(tengo|tiene|tienen|padezco|sufro|me diagnosticaron|me detectaron)\b.*"
    r"\b(fabry|pompe|gaucher|asmd|mps|mucopolisacaridosis|niemann|enfermedad|lisosomal)\b",
    r"\b(me duele|me duelen|siento|tengo)\b.*\b(dolor|cansancio|debilidad|mareos|fiebre)\b",
    r"\b(mi|mis)\b.*\b(resultado|resultados|variante|variantes|informe)\b.*"
    r"\b(significa|quiere decir|indica|es grave|es normal|salio|dio|positivo|negativo)\b",
    # Cualquier mención de tratamiento, general o personal, se deriva al médico
    r"\b(tratamientos?|tratar|tratarse|trata|tratan|curar|curarse|cura|terapias?|"
    r"medicamentos?|medicacion|remedios?|dosis|drogas?|farmacos?|inyecciones|infusiones)\b",
    r"\b(debo|tengo que|puedo|deberia)\b.*\b(tomar|tratar|medicar|operar)\b",
    r"\b(estoy|esta|esta mi (hijo|hija))\b.*\b(enfermo|enferma|sano|sana)\b",
    r"\b(me recomienda|me recomiendas|me aconseja|me aconsejas)\b",
    r"\bes (hereditario|hereditaria) (en )?(mi|mis)\b",
    r"\b(puedo|podria|sera que)\b.*\b(tener|padecer)\b",
    r"\b(estos|mis|mi)\s+sintomas?\b",
]
_REFERRAL = [re.compile(pattern) for pattern in _REFERRAL_PATTERNS]

# Frases que solo anuncian una pregunta ("tengo una duda"): no cuentan como un caso personal.
_PREAMBLE = re.compile(
    r"\b(tengo|tenia|me quedo|me quedaron)\s+(una|unas|otra|otras|alguna|algunas)?\s*"
    r"(duda|dudas|consulta|consultas|pregunta|preguntas)\b"
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
    return any(pattern.search(text) for pattern in _REFERRAL)


def is_about_genetics(message: str) -> bool:
    """Indica si la consulta menciona algún término del tema, aunque no haya texto para responderla."""
    return bool(tokenize(message) & GENERIC_DOMAIN_TERMS)
