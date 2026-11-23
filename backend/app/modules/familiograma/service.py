from datetime import date

from app.core.errors import BusinessRuleError, InvalidIntegration
from app.integrations.familiograma import (
    PATIENT_KINSHIP_ID,
    FamiliogramaInvalido,
    obtener_familiograma,
)
from app.modules.config_medica import repository as pathology_repository
from app.modules.consulta_medica.service import months_old
from app.modules.familiograma import repository

MONTHS_PER_YEAR = 12
UNKNOWN_SEX = "no_identificado"


def list_kinships() -> list[dict]:
    """Parentescos del módulo para el selector, sin el del paciente."""
    try:
        kinships = obtener_familiograma().listar_parentescos()
    except Exception:
        raise InvalidIntegration("familiograma") from None
    return [{"id": item["id"], "name": item["parentesco"]} for item in kinships]


def _get_patient(patient_id: str) -> dict:
    """Devuelve el paciente o responde 404."""
    patient = repository.find_patient(patient_id)
    if patient is None:
        raise BusinessRuleError("No hay un paciente registrado con ese id.", 404)
    return patient


def _to_relative_out(row: dict, patient_ids: dict[str, str]) -> dict:
    """Convierte la fila guardada en lo que ve la pantalla.

    `patient_ids` dice qué DNI ya son pacientes: así el vínculo se
    calcula al leer y no se desactualiza si se reemplaza la lista.
    """
    return {
        "kinship_id": row["kinship_id"],
        "first_name": row["name"],
        "last_name": row["last_name"],
        "dni": row["dni"],
        "linked_patient_id": patient_ids.get(row["dni"]),
        "sex": row["sex"],
        "age": row["age"],
        "deceased": row["deceased"],
        "symptoms": row["symptoms"],
        "pathologies": row["diagnoses"],
    }


def get_relatives(patient_id: str) -> list[dict]:
    """Devuelve los familiares guardados del paciente.

    Cada familiar con DNI trae el id del paciente que lo tiene, si ya
    es paciente.
    """
    _get_patient(patient_id)
    rows = repository.list_by_patient(patient_id)
    patient_ids = repository.find_patient_ids_by_dni([row["dni"] for row in rows if row["dni"]])
    return [_to_relative_out(row, patient_ids) for row in rows]


def save_relatives(patient_id: str, data: dict) -> list[dict]:
    """Reemplaza los familiares del paciente por la lista recibida.

    Cada diagnóstico se guarda con su id, código y nombre del catálogo,
    que es lo que el módulo pide después.
    """
    _get_patient(patient_id)
    catalog = {pathology["id"]: pathology for pathology in pathology_repository.list_all()}
    rows = []
    for relative in data["relatives"]:
        diagnoses = [
            {
                "id": pathology_id,
                "code": catalog[pathology_id]["code"],
                "name": catalog[pathology_id]["name"],
            }
            for pathology_id in relative.get("pathology_ids") or []
        ]
        symptoms = [
            {"code": symptom["code"].strip(), "term": symptom["term"].strip()}
            for symptom in relative.get("symptoms") or []
        ]
        rows.append(
            {
                "kinship_id": relative["kinship_id"],
                "name": relative["first_name"].strip(),
                "last_name": relative["last_name"].strip(),
                "dni": (relative.get("dni") or "").strip() or None,
                "sex": relative["sex"],
                "age": relative.get("age"),
                "deceased": bool(relative.get("deceased")),
                "symptoms": symptoms,
                "diagnoses": diagnoses,
            }
        )
    repository.replace_all(patient_id, rows)
    return get_relatives(patient_id)


def _patient_person(patient: dict) -> dict:
    """El paciente como persona del familiograma, con el parentesco 0.

    La edad va en años con fracción, para que un bebé no figure con 0.
    Los pacientes anteriores al campo sexo salen como no identificados.
    """
    birth_date = date.fromisoformat(patient["birth_date"])
    symptoms = [link["symptoms"] for link in patient["patient_symptoms"]]
    return {
        "parentesco": PATIENT_KINSHIP_ID,
        "nombre": patient["first_name"],
        "apellido": patient["last_name"],
        "sexo": patient["sex"] or UNKNOWN_SEX,
        "edad": round(months_old(birth_date) / MONTHS_PER_YEAR, 2),
        "sintomas": [{"codigo": s["code"], "nombre": s["term"]} for s in symptoms],
    }


def _relative_person(row: dict) -> dict:
    """Un familiar guardado, con los nombres de campo del módulo."""
    return {
        "parentesco": row["kinship_id"],
        "nombre": row["name"],
        "apellido": row["last_name"],
        "sexo": row["sex"],
        "edad": row["age"],
        "fallecido": row["deceased"],
        "sintomas": [{"codigo": s["code"], "nombre": s["term"]} for s in row["symptoms"]],
        "diagnosticos": [{"codigo": d["code"], "nombre": d["name"]} for d in row["diagnoses"]],
    }


def _rejection_message(error: FamiliogramaInvalido) -> str:
    """Arma el mensaje con el motivo de cada campo que rechazó el módulo.

    El mensaje general del módulo es siempre el mismo ("Revisá los
    campos indicados"): el motivo real viene en los detalles, con un
    código adelante (PARENTESCO_NO_RECONOCIDO: ...) que se descarta.
    """
    reasons = [detail["mensaje"].split(": ", 1)[-1] for detail in error.detalles]
    return "El módulo de familiograma rechazó los datos: " + " ".join(reasons or [error.mensaje])


def generate_family_tree(patient_id: str) -> dict:
    """Pide el familiograma al módulo con el paciente y sus familiares.

    No se guarda la imagen: se genera cada vez. Si el módulo rechaza los
    datos responde 422 con su mensaje; si no responde, 503, y los
    familiares guardados no se pierden.
    """
    patient = _get_patient(patient_id)
    people = [_patient_person(patient)]
    people += [_relative_person(row) for row in repository.list_by_patient(patient_id)]
    try:
        result = obtener_familiograma().generar_familiograma(people)
    except FamiliogramaInvalido as error:
        raise BusinessRuleError(_rejection_message(error), 422) from None
    except Exception:
        raise InvalidIntegration("familiograma") from None
    return {"warnings": result["advertencias"], "svg_base64": result["svg_base64"]}
