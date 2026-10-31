from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import dev_auth
from app.core.config import get_settings
from app.core.enums import Rol
from app.core.errors import Forbidden, InvalidSession, MustChangePassword
from app.models import user as user_model

_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
MIN_SECRET_LENGTH = 32  # para HS256, la clave tiene que tener al menos 32 caracteres

# Tipos de token. Cada uno solo sirve para lo suyo: un token de verificación no abre una sesión.
SESSION = "session"
CHALLENGE = "challenge"


def _secret() -> str:
    """Devuelve la clave con la que se firman los tokens. Sin una clave válida no se firma nada."""
    secret = get_settings().secret_key
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY no está configurada o tiene menos de {MIN_SECRET_LENGTH} caracteres."
        )
    return secret


def create_token(user_id: str, kind: str, expires_minutes: int, **claims) -> str:
    """Firma un token del tipo indicado para ese usuario.

    REUTILIZABLE: cualquier módulo que necesite un token de corta vida atado a un usuario.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "typ": kind,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        **claims,
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str, kind: str) -> dict:
    """Devuelve el contenido del token si es válido, del tipo pedido y no venció.

    Lanza `jwt.InvalidTokenError` (o una subclase) en cualquier otro caso.
    """
    claims = jwt.decode(
        token,
        _secret(),
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub", "typ"]},
    )
    if claims["typ"] != kind:
        raise jwt.InvalidTokenError("Tipo de token incorrecto.")
    return claims


def create_session_token(user_id: str) -> str:
    """Token de sesión: lo que el frontend manda en cada pedido (vence según SESSION_EXPIRE_MINUTES)."""
    return create_token(user_id, SESSION, get_settings().session_expire_minutes)


def get_session_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
):
    """Devuelve el usuario de la sesión, aunque todavía tenga que cambiar la contraseña inicial.

    Solo lo usa el endpoint de cambio de contraseña. Para todo lo demás, `get_current_user`.
    """

    # Solo con DEV_AUTH=true (desarrollo): la sesión sale de los encabezados X-Dev-*.
    simulated = dev_auth.user_from_request(request)
    if simulated is not None:
        return simulated

    if credentials is None:
        raise InvalidSession("Sesión inválida o vencida.")
    try:
        claims = decode_token(credentials.credentials, SESSION)
    except jwt.InvalidTokenError:
        raise InvalidSession("Sesión inválida o vencida.") from None

    user = user_model.find_by_id(claims["sub"])

    if user is None or user["blocked"]:
        raise InvalidSession("Sesión inválida o vencida.")

    return user


def get_current_user(user: dict = Depends(get_session_user)):
    """Devuelve el usuario de la sesión. Si tiene la contraseña inicial, no lo deja seguir."""

    if user["must_change_password"]:
        raise MustChangePassword("Tenés que cambiar la contraseña antes de continuar.")
    return user


def require_role(*roles: Rol):
    """
    Devuelve una dependencia que solo deja pasar a los usuarios con alguno de esos roles.

    Uso: usuario = Depends(require_role(Rol.MEDICO_TRATANTE))
    """

    allowed = [rol.value for rol in roles]

    def check(user: dict = Depends(get_current_user)):

        if user["role"] not in allowed:
            raise Forbidden("No tenés permiso para esta acción.")
        return user

    return check
