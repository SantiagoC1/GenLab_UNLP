import re
import unicodedata

# Palabras que no sirven para encontrar un tema.
STOPWORDS = frozenset(
    "el la los las un una unos unas de del al y o u a en con por para que como cual cuales "
    "es son ser fue sobre su sus se lo le les me mi mis te tu tus nos este esta esto estos "
    "estas ese esa eso muy mas menos hay hace hacer puede pueden tiene tienen quiero quisiera "
    "saber decir explicame explicar cuentame dime tipo".split()
)

# Palabras del tema que no alcanzan para elegir un texto (aparecen en casi todos),
# pero sí sirven para saber que la consulta es del tema.
_GENERIC_WORDS = (
    "enfermedad enfermedades patologia patologias estudio estudios genetico geneticos genetica "
    "geneticas gen genes adn analisis paciente muestra sangre laboratorio resultado resultados "
    "variante variantes mutacion mutaciones hereditaria hereditario herencia secuenciacion "
    "sintoma sintomas diagnostico"
)


def normalize(text: str) -> str:
    """Pasa a minúsculas y saca las tildes."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _stem(word: str) -> str:
    """Saca el plural más común, para que 'exomas' encuentre 'exoma'."""
    if len(word) > 4 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


GENERIC_DOMAIN_TERMS = frozenset(_stem(word) for word in _GENERIC_WORDS.split())


def tokenize(text: str) -> set[str]:
    """Devuelve las palabras con significado de un texto, normalizadas."""
    words = re.findall(r"[a-z0-9]+", normalize(text))
    return {_stem(w) for w in words if len(w) >= 3 and w not in STOPWORDS}
