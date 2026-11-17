import logging
import secrets
from datetime import date

from app.core.config import get_settings
from app.core.enums import Rol
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.database import supabase_admin
from app.integrations.apigen import obtener_apigen
from app.integrations.avisos import obtener_avisos
from app.integrations.cdss import obtener_cdss
from app.integrations.snomed import obtener_snomed
from app.modules.acceso import repository as user_repository
from app.modules.acceso.service import create_account
from app.modules.config_medica import repository as pathology_repository
from app.modules.config_medica.service import get_cdss_strategy
from app.modules.consulta_medica import repository as patient_repository

logger = logging.getLogger(__name__)

AGE_OF_MAJORITY = 18
CDSS_NOT_COMPATIBLE = "no compatible con patologías lisosomales"
POMPE_NAME = "pompe"
POMPE_URGENT_MONTHS = 4
EMAIL_UNAVAILABLE = (
    "No se puede usar ese mail para el alta. Usá otro o consultá con el administrador."
)


def search_symptoms(text: str, page: int = 1) -> dict:
    """Busca síntomas en SNOMED y devuelve solo el código y el término.

    Si falla no se loguea la búsqueda, porque puede traer datos del otro
    módulo.
    """
    try:
        result = obtener_snomed().buscar_terminos(text.strip(), page)
    except Exception:
        raise InvalidIntegration("SNOMED") from None
    return {"items": result["items"], "page": page, "has_more": result["has_more"]}


def is_minor(birth_date: date, today: date | None = None) -> bool:
    """Indica si tiene menos de 18 años cumplidos.

    De eso depende de quién es la cuenta de acceso. `today` permite
    probarla con fechas fijas.
    """
    today = today or date.today()
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    age = today.year - birth_date.year - (0 if had_birthday else 1)
    return age < AGE_OF_MAJORITY


def find_patient(dni: str) -> dict:
    """Busca un paciente por DNI; si no existe, responde 404."""
    patient = patient_repository.find_by_dni(dni.strip())
    if patient is None:
        raise BusinessRuleError("No hay un paciente registrado con ese DNI.", 404)
    return patient


def _ask_cdss(symptoms: list[dict]) -> str:
    """REUTILIZABLE. Pregunta al CDSS qué patología corresponde.

    Si no responde, 503: sin su respuesta no se puede verificar la
    sospecha.
    """
    strategy = get_cdss_strategy()
    codes = [symptom["code"] for symptom in symptoms]
    try:
        return obtener_cdss().sintomas_a_patologia(codes, strategy)
    except Exception:
        raise InvalidIntegration("CDSS") from None


def _check_clinical_match(symptoms: list[dict], chosen: list[dict]) -> None:
    """Acepta la sospecha clínica si el CDSS devuelve una patología elegida.

    Si no, bloquea el alta (422) y dice qué síntoma cardinal se
    esperaba.
    """
    answer = _ask_cdss(symptoms)
    chosen_names = {pathology_repository.name_key(pathology["name"]) for pathology in chosen}
    if pathology_repository.name_key(answer) in chosen_names:
        return

    expected = [
        f"para {pathology['name']} se espera el síntoma cardinal «{pathology['cardinal']['term']}»"
        for pathology in chosen
        if pathology["cardinal"]
    ]
    message = "Los síntomas cargados no corresponden a la patología sospechada."
    if answer != CDSS_NOT_COMPATIBLE:
        message += f" El CDSS indica: {answer}."
    if expected:
        message += " Revisá los síntomas: " + "; ".join(expected) + "."
    raise BusinessRuleError(message, 422)


def _get_or_create_account(data: dict, minor: bool) -> tuple[dict, str | None]:
    """Devuelve la cuenta del paciente y su contraseña temporal.

    Un menor usa la cuenta de su padre o madre: si ya es de un paciente
    se reutiliza, sin contraseña nueva.
    """
    email = data["email"].strip().lower()
    existing = user_repository.find_by_email(email)
    if existing is not None:
        if not minor or existing["role"] != Rol.PACIENTE.value:
            raise BusinessRuleError(EMAIL_UNAVAILABLE, 422)
        return existing, None

    password = secrets.token_urlsafe(9)
    account = {
        "role": Rol.PACIENTE.value,
        "email": email,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "phone": data["phone"],
    }
    return create_account(account, password, must_change_password=True), password


def _delete_account(user_id: str) -> None:
    """Borra el usuario de Auth; la fila de `users` se borra en cascada."""
    supabase_admin.auth.admin.delete_user(user_id)


def _send_credentials(user: dict, password: str, doctor: dict) -> bool:
    """Envía por mail el usuario y la contraseña inicial y devuelve si se pudo.

    Con el simulador solo se loguea el destinatario, nunca la
    contraseña.
    """
    message = (
        f"{doctor['first_name']} {doctor['last_name']} te dio de alta como paciente en GenLab. "
        f"Tus credenciales de acceso: usuario {user['email']}, contraseña inicial {password}. "
        "Vas a tener que cambiarla en tu primer ingreso."
    )
    if get_settings().integracion_avisos == "simulador":
        logger.warning("[simulador de avisos] credenciales enviadas a %s", user["email"])
    try:
        return bool(obtener_avisos().enviar_aviso(user["email"], "mail", message))
    except Exception:
        return False


def create_patient(data: dict, doctor: dict) -> dict:
    """Da de alta al paciente, crea su cuenta y le envía las credenciales."""
    if patient_repository.find_by_dni(data["dni"].strip()) is not None:
        raise BusinessRuleError("Ya existe un paciente con ese DNI.", 409, code="patient_exists")

    symptoms = [
        {"code": symptom["code"].strip(), "term": symptom["term"].strip()}
        for symptom in data.get("symptoms") or []
    ]
    pathology_ids = data["pathology_ids"]
    if data["suspicion_type"] == "clinica":
        chosen = [p for p in pathology_repository.list_all() if p["id"] in pathology_ids]
        _check_clinical_match(symptoms, chosen)

    birth_date = date.fromisoformat(data["birth_date"].strip())
    account, password = _get_or_create_account(data, is_minor(birth_date))
    account_created = password is not None

    row = {
        "account_user_id": account["id"],
        "dni": data["dni"].strip(),
        "first_name": data["first_name"].strip(),
        "last_name": data["last_name"].strip(),
        "birth_date": birth_date.isoformat(),
        "phone": data["phone"].strip(),
        "clinical_summary": data["clinical_summary"].strip(),
        "suspicion_type": data["suspicion_type"],
        "registered_by": doctor["id"],
    }
    try:
        patient = patient_repository.create(row, pathology_ids, symptoms)
    except patient_repository.DniTaken:
        if account_created:
            _delete_account(account["id"])
        raise BusinessRuleError(
            "Ya existe un paciente con ese DNI.", 409, code="patient_exists"
        ) from None
    except Exception:
        if account_created:
            _delete_account(account["id"])
        raise

    if account_created and not _send_credentials(account, password, doctor):
        patient_repository.delete(patient["id"])
        _delete_account(account["id"])
        raise InvalidIntegration("avisos")

    return {**patient, "account_created": account_created}


def months_old(birth_date: date, today: date | None = None) -> int:
    """Meses cumplidos desde el nacimiento."""
    today = today or date.today()
    months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
    return months if today.day >= birth_date.day else months - 1


def is_pompe_urgent(birth_date: date, pathologies: list[dict], today: date | None = None) -> bool:
    """Indica si hay Pompe y el paciente tiene menos de 4 meses.

    Pompe se reconoce porque su nombre contiene 'pompe'.
    """
    has_pompe = any(
        POMPE_NAME in pathology_repository.name_key(pathology["name"]) for pathology in pathologies
    )
    return has_pompe and months_old(birth_date, today) < POMPE_URGENT_MONTHS


def _ask_genes(pathologies: list[dict], with_secondary: bool) -> list[str]:
    """REUTILIZABLE. Pide a Apigen los genes de cada patología.

    Los junta sin repetir.

    Si no responde, 503 y no se crea el estudio.
    """
    try:
        apigen = obtener_apigen()
        genes = []
        for pathology in pathologies:
            for gene in apigen.genes_por_patologia(pathology["name"], with_secondary):
                if gene not in genes:
                    genes.append(gene)
        return genes
    except Exception:
        raise InvalidIntegration("Apigen") from None


def _study_genes(pathologies: list[dict], secondary_findings: bool) -> list[dict]:
    """Arma la lista de genes con su origen.

    Los que solo aparecen al pedir hallazgos secundarios quedan marcados
    como tales (P15).
    """
    base = _ask_genes(pathologies, False)
    genes = [{"gene": gene, "origin": "patologia"} for gene in base]
    if secondary_findings:
        for gene in _ask_genes(pathologies, True):
            if gene not in base:
                genes.append({"gene": gene, "origin": "hallazgo_secundario"})
    return genes


def _chosen_pathologies(pathology_ids: list[int]) -> list[dict]:
    """Las patologías del catálogo que eligió el médico."""
    return [p for p in pathology_repository.list_all() if p["id"] in pathology_ids]


def get_study_genes(pathology_ids: list[int], secondary_findings: bool) -> dict:
    """Vista previa de los genes que se analizarían para esas patologías."""
    pathologies = _chosen_pathologies(pathology_ids)
    return {"genes": _study_genes(pathologies, secondary_findings)}


def create_study(data: dict, doctor: dict) -> dict:
    """Registra el estudio en estado Creado.

    Vuelve a pedir los genes a Apigen y suma los manuales sin repetir.
    Si Apigen falla, no crea nada.
    """

    patient = patient_repository.find_by_id(data["patient_id"].strip())
    if patient is None:
        raise BusinessRuleError("No hay un paciente registrado con ese id.", 404)

    pathologies = _chosen_pathologies(data["pathology_ids"])
    secondary_findings = bool(data.get("secondary_findings"))
    genes = _study_genes(pathologies, secondary_findings)
    known = {gene["gene"] for gene in genes}
    for text in data.get("manual_genes") or []:
        gene = text.strip().upper()
        if gene and gene not in known:
            genes.append({"gene": gene, "origin": "manual"})
            known.add(gene)

    row = {
        "patient_id": patient["id"],
        "requested_by": doctor["id"],
        "secondary_findings": secondary_findings,
        "pompe_urgent": is_pompe_urgent(date.fromisoformat(patient["birth_date"]), pathologies),
    }
    study = patient_repository.create_study(row, data["pathology_ids"], genes)
    return {**study, "genes": genes}
