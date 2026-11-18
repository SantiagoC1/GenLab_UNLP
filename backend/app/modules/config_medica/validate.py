import re
import unicodedata

from app.core.enums import CdssStrategy
from app.modules.config_medica import repository

MAX_NAME_LENGTH = 100
CODE_PATTERN = re.compile(r"[A-Za-z0-9_]{1,30}")
MAX_FIELD_LENGTH = 200
MIN_SECONDARY = 2
MAX_SECONDARY = 30


def _has_control_characters(text: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def _code_key(code: str) -> str:
    """Clave para comparar códigos de síntoma sin importar el formato.

    'SIM-001' y ' sim-001 ' dan la misma clave.
    """
    return unicodedata.normalize("NFKC", code).strip().casefold()


def _is_valid_text(value) -> bool:
    text = (value or "").strip()
    return 0 < len(text) <= MAX_FIELD_LENGTH and not _has_control_characters(text)


def _is_valid_symptom(symptom) -> bool:
    return bool(symptom) and _is_valid_text(symptom["code"]) and _is_valid_text(symptom["term"])


def validate_symptoms(data: dict) -> list[str]:
    """Valida el síntoma cardinal y los secundarios (M2-RF1 y M2-RF4)."""
    errors = []
    cardinal = data.get("cardinal")
    secondary = data.get("secondary")

    cardinal_ok = _is_valid_symptom(cardinal)
    if cardinal is None:
        errors.append("Elegí el síntoma cardinal.")
    elif not cardinal_ok:
        errors.append("El síntoma cardinal no es válido.")

    if len(secondary or []) < MIN_SECONDARY:
        errors.append(f"Cargá al menos {MIN_SECONDARY} síntomas secundarios.")
        return errors
    if len(secondary) > MAX_SECONDARY:
        errors.append(f"No se pueden cargar más de {MAX_SECONDARY} síntomas secundarios.")
        return errors
    if not all(_is_valid_symptom(symptom) for symptom in secondary):
        errors.append("Hay un síntoma secundario que no es válido.")
        return errors

    codes = [_code_key(symptom["code"]) for symptom in secondary]
    if len(set(codes)) != len(codes):
        errors.append("Los síntomas secundarios no pueden repetirse.")
    if cardinal_ok and _code_key(cardinal["code"]) in codes:
        errors.append("El síntoma cardinal no puede repetirse como secundario.")
    return errors


def _validate_code(code) -> list[str]:
    """Valida el código que usan Apigen y el CDSS, por ejemplo POMPE.

    Solo letras, números y guion bajo, sin repetirse.
    """
    if not (code and code.strip()):
        return ["Ingresá el código de la patología."]
    if not CODE_PATTERN.fullmatch(code.strip()):
        return ["El código solo puede tener letras, números y guion bajo (hasta 30)."]
    if repository.code_exists(code):
        return ["Ya existe una patología con ese código."]
    return []


def validate_pathology(data: dict) -> list[str]:
    """Valida el alta de una patología: nombre, código y síntomas."""
    errors = []
    name = data.get("name")
    if not (name and name.strip()):
        errors.append("Ingresá el nombre de la patología.")
    elif _has_control_characters(name):
        errors.append("El nombre no puede tener caracteres de control.")
    elif len(repository.normalize_name(name)) > MAX_NAME_LENGTH:
        errors.append(f"El nombre no puede tener más de {MAX_NAME_LENGTH} caracteres.")
    elif repository.name_exists(name):
        errors.append("Ya existe una patología con ese nombre.")
    return errors + _validate_code(data.get("code")) + validate_symptoms(data)


def validate_cdss_strategy(data: dict) -> list[str]:
    """Valida que la estrategia sea una de las tres permitidas (M2-RF5)."""
    if data.get("strategy") not in set(CdssStrategy):
        return ["Elegí una de las estrategias del CDSS."]
    return []
