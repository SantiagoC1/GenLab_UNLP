"""Validaciones de los datos de M3. Cada función devuelve una lista de errores:
si la lista está vacía, los datos son válidos.

SUPUESTOS (docs/Supuestos_y_pendientes.md, S3 y S4): la especificación pide "tres letras o más"
y "paginación" sin más detalle. Se cuentan caracteres tras recortar los espacios, y los topes
protegen al módulo externo de pedidos desmedidos. Los topes del alta de paciente (nombre,
teléfono, mail y resumen) son propios: la especificación no los fija.
"""

import re
from datetime import date

from app.modules.acceso.validate import EMAIL_PATTERN, FIELD_LABELS, required_field_error
from app.modules.config_medica import repository as pathology_repository

MIN_SEARCH_LENGTH = 3
MAX_SEARCH_LENGTH = 100
MAX_PAGE = 100

MAX_FIELD_LENGTH = 200
MAX_NAME_LENGTH = 100
MAX_PHONE_LENGTH = 30
MAX_EMAIL_LENGTH = 254
MAX_SUMMARY_LENGTH = 5000
ONE_LINE_FIELDS = {
    "first_name": MAX_NAME_LENGTH,
    "last_name": MAX_NAME_LENGTH,
    "phone": MAX_PHONE_LENGTH,
    "email": MAX_EMAIL_LENGTH,
}
SUSPICION_TYPES = ("clinica", "familiar")
DNI_PATTERN = re.compile(r"[0-9]{7,8}")
REQUIRED_PATIENT_FIELDS = (
    "dni",
    "first_name",
    "last_name",
    "birth_date",
    "phone",
    "email",
    "suspicion_type",
    "clinical_summary",
)


def _has_control_characters(text: str) -> bool:
    """Indica si el texto tiene caracteres de control (saltos de línea, tabulaciones, NUL...)."""
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def validate_symptom_search(text: str | None, page: str | None) -> list[str]:
    """Valida el texto a buscar y el número de página (que llega como texto de la URL).

    La página se acepta solo si son dígitos ASCII: `isascii` evita que `int()` convierta dígitos
    de otros alfabetos.
    """
    errors = []

    stripped = (text or "").strip()
    if len(stripped) < MIN_SEARCH_LENGTH:
        errors.append(f"Escribí al menos {MIN_SEARCH_LENGTH} letras para buscar un síntoma.")
    elif len(stripped) > MAX_SEARCH_LENGTH:
        errors.append(f"La búsqueda no puede tener más de {MAX_SEARCH_LENGTH} caracteres.")
    elif _has_control_characters(stripped):
        errors.append("La búsqueda tiene caracteres que no se pueden usar.")

    if page is not None:
        is_number = page.isascii() and page.isdigit() and len(page) <= 6
        if not is_number or not 1 <= int(page) <= MAX_PAGE:
            errors.append(f"La página tiene que ser un número entre 1 y {MAX_PAGE}.")

    return errors


def validate_dni_search(dni: str | None) -> list[str]:
    """Valida el DNI con el que se busca a un paciente (M3-RF7)."""
    if not DNI_PATTERN.fullmatch((dni or "").strip()):
        return ["El DNI tiene que tener 7 u 8 dígitos."]
    return []


def _is_filled(value) -> bool:
    """Un campo de texto está completo si es un texto con algo más que espacios."""
    return isinstance(value, str) and value.strip() != ""


def _is_valid_symptom(symptom) -> bool:
    """Un síntoma es válido si trae un código y un término de texto, no vacíos y no desmedidos."""
    if not isinstance(symptom, dict):
        return False
    for field in ("code", "term"):
        value = symptom.get(field)
        if not _is_filled(value) or len(value.strip()) > MAX_FIELD_LENGTH:
            return False
    return True


def _validate_birth_date(birth_date: str) -> list[str]:
    """La fecha tiene que ser real (AAAA-MM-DD) y no puede ser futura."""
    try:
        parsed = date.fromisoformat(birth_date.strip())
    except ValueError:
        return ["La fecha de nacimiento no es válida."]
    if parsed > date.today():
        return ["La fecha de nacimiento no puede ser futura."]
    return []


def _validate_pathology_ids(pathology_ids) -> list[str]:
    """Hay que elegir al menos un diagnóstico presuntivo, sin repetir y del catálogo (M3-RF3)."""
    if not pathology_ids:
        return ["Elegí al menos un diagnóstico presuntivo."]
    if len(set(pathology_ids)) != len(pathology_ids):
        return ["Los diagnósticos presuntivos no pueden repetirse."]
    catalog_ids = {pathology["id"] for pathology in pathology_repository.list_all()}
    if not set(pathology_ids) <= catalog_ids:
        return ["Algún diagnóstico presuntivo no está en el catálogo."]
    return []


def _validate_patient_symptoms(symptoms, suspicion_type) -> list[str]:
    """En una sospecha clínica los síntomas son obligatorios; en una familiar pueden faltar (P1)."""
    symptoms = symptoms or []
    if suspicion_type == "clinica" and not symptoms:
        return ["En una sospecha clínica cargá al menos un síntoma."]
    if not all(_is_valid_symptom(symptom) for symptom in symptoms):
        return ["Hay un síntoma que no es válido."]
    codes = [symptom["code"].strip() for symptom in symptoms]
    if len(set(codes)) != len(codes):
        return ["Los síntomas no pueden repetirse."]
    return []


def _validate_patient_text_sizes(data: dict) -> list[str]:
    """Pone tope al largo de los textos del alta y rechaza caracteres de control en los de una línea.

    Existe para que nadie guarde un resumen de megabytes ni un nombre con saltos de línea. El
    resumen clínico puede tener varias líneas, así que solo se le limita el largo.
    """
    errors = []
    for field, max_length in ONE_LINE_FIELDS.items():
        value = data.get(field)
        if not _is_filled(value):
            continue
        label = FIELD_LABELS[field]
        if len(value.strip()) > max_length:
            errors.append(f"El campo '{label}' no puede tener más de {max_length} caracteres.")
        elif _has_control_characters(value.strip()):
            errors.append(f"El campo '{label}' tiene caracteres que no se pueden usar.")
    summary = data.get("clinical_summary")
    if _is_filled(summary) and len(summary.strip()) > MAX_SUMMARY_LENGTH:
        label = FIELD_LABELS["clinical_summary"]
        errors.append(f"El campo '{label}' no puede tener más de {MAX_SUMMARY_LENGTH} caracteres.")
    return errors


def validate_patient(data: dict) -> list[str]:
    """Valida el alta de un paciente (escenario 9) y junta todos los errores.

    Primero revisa los campos obligatorios. Después, solo de los que están completos, revisa su
    formato: así un campo vacío no genera dos mensajes.
    """
    errors = []
    for field in REQUIRED_PATIENT_FIELDS:
        if not _is_filled(data.get(field)):
            errors.append(required_field_error(field))

    if _is_filled(data.get("dni")) and not DNI_PATTERN.fullmatch(data["dni"].strip()):
        errors.append("El DNI tiene que tener 7 u 8 dígitos.")
    if _is_filled(data.get("email")) and not EMAIL_PATTERN.match(data["email"].strip()):
        errors.append("El mail no tiene un formato válido.")
    if _is_filled(data.get("birth_date")):
        errors += _validate_birth_date(data["birth_date"])

    suspicion_type = data.get("suspicion_type")
    if _is_filled(suspicion_type) and suspicion_type not in SUSPICION_TYPES:
        errors.append("El tipo de sospecha tiene que ser clínica o familiar.")

    errors += _validate_patient_text_sizes(data)
    errors += _validate_pathology_ids(data.get("pathology_ids"))
    errors += _validate_patient_symptoms(data.get("symptoms"), suspicion_type)
    return errors
