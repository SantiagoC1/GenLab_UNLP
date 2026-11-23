from app.modules.acceso.validate import FIELD_LABELS, required_field_error
from app.modules.config_medica import repository as pathology_repository
from app.modules.consulta_medica.validate import (
    MAX_NAME_LENGTH,
    SEXES,
    _has_control_characters,
    _is_filled,
    _is_valid_symptom,
)

MAX_RELATIVES = 30
MAX_SYMPTOMS = 30
MAX_AGE = 120
PATIENT_KINSHIP_ID = 0


def _validate_name(relative: dict, field: str) -> list[str]:
    """El nombre y el apellido son obligatorios, cortos y de una línea."""
    value = relative.get(field)
    if not _is_filled(value):
        return [required_field_error(field)]
    label = FIELD_LABELS[field]
    if len(value.strip()) > MAX_NAME_LENGTH:
        return [f"El campo '{label}' no puede tener más de {MAX_NAME_LENGTH} caracteres."]
    if _has_control_characters(value.strip()):
        return [f"El campo '{label}' tiene caracteres que no se pueden usar."]
    return []


def _validate_symptoms(symptoms) -> list[str]:
    """Los síntomas tienen que ser válidos, pocos y sin repetir."""
    symptoms = symptoms or []
    if len(symptoms) > MAX_SYMPTOMS:
        return [f"No se pueden cargar más de {MAX_SYMPTOMS} síntomas."]
    if not all(_is_valid_symptom(symptom) for symptom in symptoms):
        return ["Hay un síntoma que no es válido."]
    codes = [symptom["code"].strip() for symptom in symptoms]
    if len(set(codes)) != len(codes):
        return ["Los síntomas no pueden repetirse."]
    return []


def _validate_pathology_ids(pathology_ids, catalog_ids: set[int]) -> list[str]:
    """Los diagnósticos son del catálogo y no se repiten."""
    pathology_ids = pathology_ids or []
    if len(set(pathology_ids)) != len(pathology_ids):
        return ["Los diagnósticos no pueden repetirse."]
    if not set(pathology_ids) <= catalog_ids:
        return ["Algún diagnóstico no está en el catálogo."]
    return []


def _validate_relative(relative: dict, catalog_ids: set[int]) -> list[str]:
    """Valida un familiar y junta todos sus errores."""
    errors = []
    kinship_id = relative.get("kinship_id")
    if kinship_id is None:
        errors.append(required_field_error("kinship_id"))
    elif kinship_id == PATIENT_KINSHIP_ID:
        errors.append("El parentesco no puede ser el del paciente.")

    errors += _validate_name(relative, "first_name")
    errors += _validate_name(relative, "last_name")

    sex = relative.get("sex")
    if not _is_filled(sex):
        errors.append(required_field_error("sex"))
    elif sex not in SEXES:
        errors.append("El sexo tiene que ser hombre, mujer o no identificado.")

    age = relative.get("age")
    if age is not None and not 0 <= age <= MAX_AGE:
        errors.append(f"La edad tiene que estar entre 0 y {MAX_AGE} años.")

    errors += _validate_symptoms(relative.get("symptoms"))
    errors += _validate_pathology_ids(relative.get("pathology_ids"), catalog_ids)
    return errors


def validate_relatives(data: dict) -> list[str]:
    """Valida la lista de familiares y junta los errores de todos.

    Cada mensaje dice a qué familiar corresponde. La edad puede faltar
    (desconocida). Una lista vacía es válida: borra los familiares.
    """
    relatives = data.get("relatives")
    if relatives is None:
        return ["Mandá la lista de familiares."]
    if len(relatives) > MAX_RELATIVES:
        return [f"No se pueden cargar más de {MAX_RELATIVES} familiares."]

    catalog_ids = {pathology["id"] for pathology in pathology_repository.list_all()}
    errors = []
    for number, relative in enumerate(relatives, start=1):
        errors += [
            f"Familiar {number}: {error}" for error in _validate_relative(relative, catalog_ids)
        ]
    return errors
