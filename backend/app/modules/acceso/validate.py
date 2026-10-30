"""Validaciones de los datos de M1. Cada función devuelve una lista de errores:
si la lista está vacía, los datos son válidos."""

import re

from app.models import specialty as specialty_model
from app.models import user as user_model
from app.modules.acceso.catalogs import PROVINCES

MIN_PASSWORD_LENGTH = 8  # la especificación no define una política de contraseñas
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Nombre de cada campo tal como se le muestra a la persona (los identificadores van en inglés).
# REUTILIZABLE: las validaciones de otros módulos (por ejemplo, el alta de paciente en M3)
# pueden usarlo para armar sus mensajes.
FIELD_LABELS = {
    "role": "rol",
    "first_name": "nombre",
    "last_name": "apellido",
    "phone": "teléfono",
    "email": "mail",
    "password": "contraseña",
    "current_password": "contraseña actual",
    "new_password": "contraseña nueva",
    "confirmation": "confirmación de la contraseña",
    "code": "código",
}


def required_field_error(field: str) -> str:
    """Mensaje de campo obligatorio, con el nombre del campo en español."""
    return f"El campo '{FIELD_LABELS.get(field, field)}' es obligatorio."


def validate_login(data: dict) -> list[str]:
    """Valida que el primer paso del ingreso traiga el mail y la contraseña."""
    if not data.get("email") or not data.get("password"):
        return ["Completá el mail y la contraseña."]
    return []


def validate_code(data: dict) -> list[str]:
    """Valida que el segundo paso del ingreso traiga el mail, el código y el token del paso 1."""
    errors = []
    if not data.get("email") or not data.get("code"):
        errors.append("Completá el mail y el código.")
    if not data.get("challenge"):
        errors.append("Volvé a ingresar con tu contraseña para recibir un código.")
    return errors


def validate_user_data(data: dict, allowed_roles: tuple, with_password: bool) -> list[str]:
    """Valida el alta de un usuario (autoalta o alta del administrador).

    Args:
        data: los datos recibidos (role, first_name, last_name, phone, email, password,
            license_number, specialties, province).
        allowed_roles: los roles que se pueden dar de alta por este camino.
        with_password: True si la contraseña la define la persona (autoalta).
    Returns:
        La lista de mensajes de error. Vacía si los datos son válidos.
    """
    errors = []

    required = ["role", "first_name", "last_name", "phone", "email"]
    if with_password:
        required.append("password")
    for field in required:
        if not (data.get(field) or "").strip():
            errors.append(required_field_error(field))

    email = (data.get("email") or "").strip()
    if email:
        if not EMAIL_PATTERN.match(email):
            errors.append("El mail no tiene un formato válido.")
        elif user_model.find_by_email(email) is not None:
            errors.append("Ya existe un usuario con ese mail.")

    password = data.get("password")
    if password and len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")

    role = data.get("role")
    if role and role not in allowed_roles:
        errors.append("Ese rol no se puede dar de alta por este camino.")

    if role == "medico_tratante":
        if not (data.get("license_number") or "").strip():
            errors.append("El médico tratante debe indicar su matrícula.")
        errors += _validate_specialties(data.get("specialties"))

    if role == "transportista":
        province = data.get("province")
        if not province:
            errors.append("El transportista debe indicar la provincia que cubre.")
        elif province not in PROVINCES:
            errors.append("La provincia no está en el catálogo.")
        elif user_model.carrier_exists_in(province):
            errors.append(f"Ya hay un transportista para {province}.")

    return errors


def _validate_specialties(specialty_ids: list | None) -> list[str]:
    """Valida que haya al menos una especialidad y que todas estén en el catálogo."""
    if not specialty_ids:
        return ["El médico tratante debe indicar al menos una especialidad."]
    catalog_ids = {specialty["id"] for specialty in specialty_model.list_all()}
    if not set(specialty_ids) <= catalog_ids:
        return ["Alguna especialidad no está en el catálogo."]
    return []


def validate_password_change(data: dict) -> list[str]:
    """Valida el cambio de contraseña: que estén los tres datos, que la nueva sea larga
    y que coincida con la confirmación (escenario 3)."""
    errors = []
    for field in ("current_password", "new_password", "confirmation"):
        if not data.get(field):
            errors.append(required_field_error(field))
    new_password = data.get("new_password")
    if new_password and len(new_password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if new_password and data.get("confirmation") and new_password != data["confirmation"]:
        errors.append("Las contraseñas no coinciden.")
    return errors
