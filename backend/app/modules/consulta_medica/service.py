import logging
import secrets
from datetime import date

from app.core.config import get_settings
from app.core.enums import Rol
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.database import supabase_admin
from app.integrations.avisos import obtener_avisos
from app.integrations.cdss import obtener_cdss
from app.integrations.snomed import obtener_snomed
from app.modules.acceso import repository as user_repository
from app.modules.acceso.service import create_account
from app.modules.config_medica import repository as pathology_repository
from app.modules.config_medica.service import get_cdss_strategy
from app.modules.consulta_medica import repository as patient_repository

logger = logging.getLogger(__name__)

MAX_FIELD_LENGTH = 200
AGE_OF_MAJORITY = 18
CDSS_NOT_COMPATIBLE = "no compatible con patologías lisosomales"
EMAIL_UNAVAILABLE = (
    "No se puede usar ese mail para el alta. Usá otro o consultá con el administrador."
)


def search_symptoms(text: str, page: int = 1) -> dict:
    """Busca síntomas en SNOMED (escenario 7). Solo devuelve el código y el término.

    La respuesta del otro módulo no es de confianza: se copian solo los campos conocidos. Si falla,
    no se loguea el texto buscado ni el error, porque pueden traer datos del otro módulo.
    """
    try:
        result = obtener_snomed().buscar_terminos(text.strip(), page)
        items = [
            {
                "code": str(item["code"])[:MAX_FIELD_LENGTH],
                "term": str(item["term"])[:MAX_FIELD_LENGTH],
            }
            for item in result["items"]
        ]
        has_more = bool(result["has_more"])
    except Exception:
        raise InvalidIntegration("SNOMED") from None
    return {"items": items, "page": page, "has_more": has_more}


def is_minor(birth_date: date, today: date | None = None) -> bool:
    """Indica si la persona es menor de edad (menos de 18 años cumplidos).

    Existe porque de eso depende de quién es la cuenta de acceso (M3-RF2): un menor usa el mail
    de su padre o madre. `today` se puede pasar para probar la función con fechas fijas. Si todavía
    no llegó el cumpleaños de este año, a la resta de años hay que descontarle uno.
    """
    today = today or date.today()
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    age = today.year - birth_date.year - (0 if had_birthday else 1)
    return age < AGE_OF_MAJORITY


def find_patient(dni: str) -> dict:
    """Busca un paciente por DNI (M3-RF7). Si no está, responde 404 para que el médico lo dé de alta."""
    patient = patient_repository.find_by_dni(dni.strip())
    if patient is None:
        raise BusinessRuleError("No hay un paciente registrado con ese DNI.", 404)
    return patient


def _ask_cdss(symptoms: list[dict]) -> str:
    """Le pregunta al CDSS qué patología corresponde a los síntomas del paciente.

    REUTILIZABLE: es el único lugar que conoce cómo se le habla al CDSS (qué se le manda y qué
    devuelve). Cuando se cierre el contrato real, se cambia acá y nada más.
    Si el CDSS no responde se corta con 503: sin su respuesta no se puede verificar la regla.
    """
    strategy = get_cdss_strategy()
    codes = [symptom["code"] for symptom in symptoms]
    try:
        return obtener_cdss().sintomas_a_patologia(codes, strategy)
    except Exception:
        raise InvalidIntegration("CDSS") from None


def _check_clinical_match(symptoms: list[dict], chosen: list[dict]) -> None:
    """Regla de correspondencia clínica (M3-RF6): la decide el CDSS, no nuestro backend.

    La sospecha clínica se acepta si la patología que devuelve el CDSS es una de las que eligió
    el médico. Si no, se bloquea el alta (422) y el mensaje dice qué síntoma cardinal se esperaba
    de cada patología elegida, para que el médico vea qué falta.
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
        message += f" El CDSS indica: {str(answer)[:MAX_FIELD_LENGTH]}."
    if expected:
        message += " Revisá los síntomas: " + "; ".join(expected) + "."
    raise BusinessRuleError(message, 422)


def _get_or_create_account(data: dict, minor: bool, doctor: dict) -> tuple[dict, str | None]:
    """Devuelve la cuenta de acceso del paciente y su contraseña temporal.

    Un adulto siempre recibe una cuenta nueva: si su mail ya existe, se rechaza. Un menor usa la
    cuenta de su padre o madre: si ese mail ya es de un paciente (por ejemplo un hermano), se
    reutiliza y la contraseña es None, porque no hay credenciales nuevas que enviar. Si el mail es
    de otro rol, se rechaza.

    Ambos rechazos dan el mismo mensaje, para que nadie pueda averiguar qué mails están
    registrados ni con qué rol. Cada reutilización de una cuenta queda en el log con los ids del
    médico y de la cuenta (nunca datos personales), porque el sistema no puede comprobar que ese
    mail sea realmente el del padre o madre (pendiente en Supuestos_y_pendientes.md, A3).
    """
    email = data["email"].strip().lower()
    existing = user_repository.find_by_email(email)
    if existing is not None:
        if not minor or existing["role"] != Rol.PACIENTE.value:
            raise BusinessRuleError(EMAIL_UNAVAILABLE, 422)
        logger.info(
            "Cuenta %s reutilizada por el médico %s para dar de alta a un menor",
            existing["id"],
            doctor["id"],
        )
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
    """Borra la cuenta recién creada: el usuario de Supabase Auth.

    Alcanza con borrar el de Auth porque la fila de `users` se borra en cascada. Se hace en ese
    orden para que, si falla, no quede un usuario de Auth con contraseña válida y sin su fila.
    """
    supabase_admin.auth.admin.delete_user(user_id)


def _undo(patient_id: str | None = None, account_id: str | None = None) -> None:
    """Deshace lo creado por un alta que falló: primero el paciente y después su cuenta.

    Cada paso va por separado: si uno falla, se registra el error (sin datos personales) y se
    sigue con el otro. Así una falla al deshacer no tapa el error original que hizo falta
    deshacer, que quien llama vuelve a lanzar.
    """
    if patient_id is not None:
        try:
            patient_repository.delete(patient_id)
        except Exception:
            logger.exception("No se pudo deshacer el alta: falló el borrado del paciente")
    if account_id is not None:
        try:
            _delete_account(account_id)
        except Exception:
            logger.exception("No se pudo deshacer el alta: falló el borrado de la cuenta")


def _send_credentials(user: dict, password: str, doctor: dict) -> bool:
    """Envía por mail el usuario y la contraseña inicial (M3-RF8). Devuelve si se pudo enviar.

    Con el simulador de avisos solo se loguea el destinatario: el mensaje lleva la contraseña
    inicial y los logs no deben guardarla.
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
    """Escenario 9: da de alta al paciente, crea su cuenta y le envía las credenciales.

    Los datos ya llegan validados. El orden importa porque no hay transacciones: primero todo lo
    que no escribe nada (DNI repetido y regla del CDSS), después la cuenta, el paciente y el mail.
    Si un paso falla, se deshacen los anteriores para no dejar una cuenta o un paciente a medias.
    """
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
    account, password = _get_or_create_account(data, is_minor(birth_date), doctor)
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
        _undo(account_id=account["id"] if account_created else None)
        raise BusinessRuleError(
            "Ya existe un paciente con ese DNI.", 409, code="patient_exists"
        ) from None
    except Exception:
        _undo(account_id=account["id"] if account_created else None)
        raise

    if account_created and not _send_credentials(account, password, doctor):
        _undo(patient_id=patient["id"], account_id=account["id"])
        raise InvalidIntegration("avisos")

    return {**patient, "account_created": account_created}
