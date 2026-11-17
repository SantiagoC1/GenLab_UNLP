"""Development-only authentication bypass.

With `DEV_AUTH=true` the backend accepts the headers `X-Dev-Role` (and optionally `X-Dev-User`)
and builds the session from them, so the screens can be browsed before the real login is used.
With `DEV_AUTH` unset or false (the default) nothing in this module has any effect: the headers
are ignored and the normal token check applies.

NEVER enable it outside a developer's machine.
"""

import logging

from fastapi import Request

from app.core.config import get_settings
from app.core.enums import Rol

ROLE_HEADER = "X-Dev-Role"
USER_HEADER = "X-Dev-User"

logger = logging.getLogger("genlab.dev_auth")

# Accounts of the demo data (see `app/dev_demo.py`): the patient and the doctor own studies.
_DEMO_EMAILS = {
    Rol.PACIENTE: "lucia.fernandez@example.com",
    Rol.MEDICO_TRATANTE: "ana.perez@example.com",
}


def is_enabled() -> bool:
    return get_settings().dev_auth is True


def warn_if_enabled() -> None:
    if is_enabled():
        logger.warning(
            "DEV_AUTH está activo: el backend acepta el encabezado %s sin contraseña. "
            "Usarlo solo en desarrollo.",
            ROLE_HEADER,
        )


def user_from_request(request: Request) -> dict | None:
    """The simulated session user, or None when the bypass is off or the headers are missing."""
    if not is_enabled():
        return None
    value = request.headers.get(ROLE_HEADER)
    try:
        role = Rol(value) if value else None
    except ValueError:
        return None
    if role is None:
        return None
    email = request.headers.get(USER_HEADER) or _DEMO_EMAILS.get(
        role, f"dev-{role.value}@example.com"
    )
    return {
        "id": f"dev-{role.value}",
        "email": email,
        "first_name": "Dev",
        "last_name": role.value,
        "role": role.value,
        "blocked": False,
        "failed_attempts": 0,
        "must_change_password": False,
    }
