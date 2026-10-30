import hashlib
import logging
import secrets
from typing import NoReturn

import jwt
from supabase import AuthApiError, PostgrestAPIError

from app.core.config import get_settings
from app.core.errors import (
    AccountBlocked,
    BusinessRuleError,
    InvalidIntegration,
    TooManyRequests,
    Unauthenticated,
)
from app.core.security import CHALLENGE, create_session_token, create_token, decode_token
from app.database import new_auth_client, supabase_admin
from app.integrations.avisos import obtener_avisos
from app.models import specialty as specialty_model
from app.models import trusted_device as trusted_device_model
from app.models import user as user_model
from app.modules.acceso.catalogs import PROVINCES

logger = logging.getLogger(__name__)

UNIQUE_VIOLATION = "23505"  # código de Postgres para una clave única repetida


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


def _is_unique_violation(error: Exception, column: str) -> bool:
    """Indica si el error de la base es una clave única repetida sobre esa columna."""
    if not isinstance(error, PostgrestAPIError):
        return False
    info = error.json()
    return info.get("code") == UNIQUE_VIOLATION and column in (info.get("details") or "")


def create_account(data: dict, password: str, must_change_password: bool):
    """Crea el usuario en Supabase Auth y guarda sus datos en la tabla `users`.

    Si falla al guardar los datos, borra el usuario de Auth para no dejarlo a medias.
    Solo guarda la provincia, la matrícula y las especialidades de los roles que las usan.

    REUTILIZABLE: M3 (alta de paciente) crea la cuenta del paciente con esta función, con
    `must_change_password=True` y una contraseña temporal. `data` tiene que traer `role`,
    `email`, `first_name`, `last_name` y `phone`, ya validados.
    """
    email = data["email"].strip().lower()
    try:
        auth_user = supabase_admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    except AuthApiError as error:
        if error.code == "email_exists":
            raise BusinessRuleError("Ya existe un usuario con ese mail.", 422) from None
        # Un dato que Auth rechaza (mail inválido, contraseña débil) es un error de quien lo
        # envía; una falla del servidor de Auth (5xx) no lo es y se propaga.
        if error.status < 500:
            raise BusinessRuleError(
                "No se pudo crear la cuenta. Revisá el mail y la contraseña.", 422
            ) from None
        raise

    role = data["role"]
    is_carrier = role == "transportista"
    is_doctor = role == "medico_tratante"
    province = data.get("province") if is_carrier else None
    try:
        return user_model.create(
            {
                "id": auth_user.user.id,
                "email": email,
                "first_name": data["first_name"].strip(),
                "last_name": data["last_name"].strip(),
                "phone": data["phone"].strip(),
                "role": role,
                "province": province,
                "license_number": data.get("license_number") if is_doctor else None,
                "specialty_ids": (data.get("specialties") or []) if is_doctor else [],
                "must_change_password": must_change_password,
            }
        )
    except Exception as error:
        supabase_admin.auth.admin.delete_user(auth_user.user.id)
        # Dos altas a la vez para la misma provincia: la validación no lo detectó y lo frena
        # el índice único de la base (M1-RF5).
        if is_carrier and _is_unique_violation(error, "province"):
            raise BusinessRuleError(f"Ya hay un transportista para {province}.", 422) from None
        raise


def register_user(data: dict):
    """Autoalta (M1-RF1 a RF3). Devuelve el token de la sesión y el usuario creado.

    Queda con la sesión iniciada, en la vista de su rol. Pendiente P11: si el alta de
    administrativos y bioinformáticos necesita una aprobación.
    """
    user = create_account(data, data["password"], must_change_password=False)
    return create_session_token(user["id"]), user


def create_user_as_admin(data: dict, admin_user: dict):
    """Alta por el administrador general (M1-RF4 a RF6).

    Crea el usuario con una contraseña temporal y le envía las credenciales por mail.
    Si el mail no sale, el alta se deshace.
    """
    password = secrets.token_urlsafe(9)
    user = create_account(data, password, must_change_password=True)
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


def _hash_device(device_id: str | None) -> str | None:
    """Hash del identificador del navegador: en la base nunca se guarda el original."""
    if not device_id:
        return None
    return hashlib.sha256(device_id.encode()).hexdigest()


def login_user(email: str, password: str, device_id: str | None = None):
    """Paso 1 del ingreso: valida la contraseña (M1-RF8 a RF10).

    Si el dispositivo ya es de confianza, abre la sesión. Si es nuevo, envía el código de
    verificación por mail y devuelve un token de verificación, que el paso 2 exige.
    El código lo genera y lo envía Supabase (vence a los 10 minutos, M1-RF10).
    Pedir un código nuevo es volver a llamar a esta función.

    Devuelve `{"state": "authenticated", "token", "user"}` o `{"state": "code_sent", "challenge"}`.
    """
    user = _get_active_user(email)
    try:
        new_auth_client().auth.sign_in_with_password({"email": user["email"], "password": password})
    except Exception:
        _fail(user, "Credenciales inválidas.")

    device_hash = _hash_device(device_id)
    if device_hash and trusted_device_model.exists(user["id"], device_hash):
        user_model.update(user["id"], {"failed_attempts": 0})
        return {"state": "authenticated", "token": create_session_token(user["id"]), "user": user}

    try:
        new_auth_client().auth.sign_in_with_otp(
            {"email": user["email"], "options": {"should_create_user": False}}
        )
    except AuthApiError as error:
        # Supabase no deja mandar dos mails seguidos al mismo usuario
        if error.code == "over_email_send_rate_limit" or error.status == 429:
            raise TooManyRequests("Esperá un momento antes de pedir otro código.") from None
        raise InvalidIntegration("mail") from None
    except Exception:
        raise InvalidIntegration("mail") from None
    challenge = create_token(
        user["id"], CHALLENGE, get_settings().code_expire_minutes, dev=device_hash
    )
    return {"state": "code_sent", "challenge": challenge}


def verify_login_code(email: str, code: str, challenge: str, device_id: str | None = None):
    """Paso 2 del ingreso: valida el código. Devuelve el token de la sesión y el usuario.

    Exige el token de verificación del paso 1: sin haber ingresado la contraseña, el código
    solo no alcanza. Si el código es correcto, el dispositivo queda como de confianza.
    """
    user = _get_active_user(email)
    device_hash = _hash_device(device_id)
    try:
        claims = decode_token(challenge, CHALLENGE)
    except jwt.InvalidTokenError:
        raise Unauthenticated("Volvé a ingresar con tu contraseña.") from None
    if claims["sub"] != user["id"] or claims.get("dev") != device_hash:
        raise Unauthenticated("Volvé a ingresar con tu contraseña.")

    try:
        new_auth_client().auth.verify_otp({"email": user["email"], "token": code, "type": "email"})
    except Exception:
        _fail(user, "Código inválido o vencido.")

    user_model.update(user["id"], {"failed_attempts": 0})
    if device_hash:
        trusted_device_model.add(user["id"], device_hash)
    return create_session_token(user["id"]), user


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


def unblock_user(user_id: str):
    """Desbloquea una cuenta y reinicia sus intentos fallidos (M1-RF9, pendiente P12).

    Solo lo llama el administrador general (el router lo restringe).
    """
    user = user_model.find_by_id(user_id)
    if user is None:
        raise BusinessRuleError("No existe ese usuario.", 404)
    return _public_data(user_model.update(user_id, {"blocked": False, "failed_attempts": 0}))
