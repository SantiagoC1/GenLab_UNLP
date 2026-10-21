import logging
import secrets
from typing import NoReturn

from supabase import AuthApiError

from app.core.config import get_settings
from app.core.errors import (
    AccountBlocked,
    BusinessRuleError,
    InvalidIntegration,
    Unauthenticated,
)
from app.database import new_auth_client, supabase_admin
from app.integrations.avisos import obtener_avisos
from app.models import specialty as specialty_model
from app.models import user as user_model
from app.modules.acceso.catalogs import PROVINCES

logger = logging.getLogger(__name__)


def _public_data(user: dict):
    """Devuelve los datos del usuario que se muestran en la API (sin intentos fallidos, etc.)."""
    fields = ("id", "first_name", "last_name", "email", "phone", "role", "province")
    return {
        **{field: user[field] for field in fields},
        "license_number": user["license_number"],
        "blocked": user["blocked"],
    }


def get_catalogs():
    """Devuelve las especialidades y las provincias, para los formularios de alta."""
    return {"specialties": specialty_model.list_all(), "provinces": list(PROVINCES)}


def list_users():
    """Devuelve los datos de todos los usuarios, para el listado del administrador."""
    return [_public_data(user) for user in user_model.list_all()]


def _create_user(data: dict, password: str, must_change_password: bool):
    """Crea el usuario en Supabase Auth y guarda sus datos en la tabla `users`.

    Si falla al guardar los datos, borra el usuario de Auth para no dejarlo a medias.
    """
    email = data["email"].strip().lower()
    try:
        auth_user = supabase_admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    except AuthApiError as error:
        if error.code == "email_exists":
            raise BusinessRuleError("Ya existe un usuario con ese mail.", 422) from None
        raise
    try:
        return user_model.create(
            {
                "id": auth_user.user.id,
                "email": email,
                "first_name": data["first_name"].strip(),
                "last_name": data["last_name"].strip(),
                "phone": data["phone"].strip(),
                "role": data["role"],
                "province": data.get("province"),
                "license_number": data.get("license_number"),
                "specialty_ids": data.get("specialties") or [],
                "must_change_password": must_change_password,
            }
        )
    except Exception:
        supabase_admin.auth.admin.delete_user(auth_user.user.id)
        raise


def register_user(data: dict):
    """Autoalta (M1-RF1 a RF3). Devuelve el token de la sesión y el usuario creado.

    Queda con la sesión iniciada, en la vista de su rol. Pendiente P11: si el alta de
    administrativos y bioinformáticos necesita una aprobación.
    """
    user = _create_user(data, data["password"], must_change_password=False)
    session = new_auth_client().auth.sign_in_with_password(
        {"email": user["email"], "password": data["password"]}
    )
    return session.session.access_token, user


def create_user_as_admin(data: dict, admin_user: dict):
    """Alta por el administrador general (M1-RF4 a RF6).

    Crea el usuario con una contraseña temporal y le envía las credenciales por mail.
    Si el mail no sale, el alta se deshace.
    """
    password = secrets.token_urlsafe(9)
    user = _create_user(data, password, must_change_password=True)
    message = (
        f"{admin_user['first_name']} {admin_user['last_name']} te dio de alta en GenLab. "
        f"Tus credenciales de acceso: usuario {user['email']}, contraseña inicial {password}. "
        "Vas a tener que cambiarla en tu primer ingreso."
    )
    if get_settings().integracion_avisos == "simulador":
        logger.warning("[simulador de avisos] para %s: %s", user["email"], message)
    try:
        sent = obtener_avisos().enviar_aviso(user["email"], "mail", message)
    except Exception:
        sent = False
    if not sent:
        user_model.delete(user["id"])
        supabase_admin.auth.admin.delete_user(user["id"])
        raise InvalidIntegration("avisos")
    return _public_data(user)


def _get_active_user(email: str):
    """Devuelve el usuario con ese mail. Falla si no existe o si la cuenta está bloqueada."""
    user = user_model.find_by_email(email)
    # Mismo mensaje que con una contraseña incorrecta, para no revelar qué mails existen
    if user is None:
        raise Unauthenticated("Credenciales inválidas.")
    if user["blocked"]:
        raise AccountBlocked("Cuenta bloqueada.")
    return user


def _fail(user: dict, message: str) -> NoReturn:
    """Suma un intento fallido (M1-RF9) y lanza el error.

    Al llegar al límite la cuenta se bloquea, y el error es el de cuenta bloqueada.
    """
    failed_attempts = user["failed_attempts"] + 1
    blocked = failed_attempts >= get_settings().max_failed_attempts
    user_model.update(user["id"], {"failed_attempts": failed_attempts, "blocked": blocked})
    if blocked:
        raise AccountBlocked("Cuenta bloqueada por demasiados intentos fallidos.")
    raise Unauthenticated(message)


def login_user(email: str, password: str):
    """Paso 1 del ingreso: valida la contraseña y envía el código de verificación por mail.

    El código lo genera y lo envía Supabase (vence a los 10 minutos, M1-RF10).
    Pedir un código nuevo es volver a llamar a esta función.
    """
    user = _get_active_user(email)
    try:
        new_auth_client().auth.sign_in_with_password({"email": user["email"], "password": password})
    except Exception:
        _fail(user, "Credenciales inválidas.")

    try:
        new_auth_client().auth.sign_in_with_otp(
            {"email": user["email"], "options": {"should_create_user": False}}
        )
    except Exception:
        raise InvalidIntegration("mail") from None


def verify_login_code(email: str, code: str):
    """Paso 2 del ingreso: valida el código. Devuelve el token de la sesión y el usuario."""
    user = _get_active_user(email)
    try:
        response = new_auth_client().auth.verify_otp(
            {"email": user["email"], "token": code, "type": "email"}
        )
        token = response.session.access_token
    except Exception:
        _fail(user, "Código inválido o vencido.")

    user_model.update(user["id"], {"failed_attempts": 0})
    return token, user


def change_password(user: dict, current_password: str, new_password: str):
    """Cambia la contraseña del usuario (M1-RF7). Sirve para la inicial y para cambiarla después."""
    try:
        new_auth_client().auth.sign_in_with_password(
            {"email": user["email"], "password": current_password}
        )
    except Exception:
        _fail(user, "La contraseña actual es incorrecta.")

    if current_password == new_password:
        raise BusinessRuleError("La contraseña nueva tiene que ser distinta de la actual.", 422)
    supabase_admin.auth.admin.update_user_by_id(user["id"], {"password": new_password})
    user_model.update(user["id"], {"must_change_password": False, "failed_attempts": 0})