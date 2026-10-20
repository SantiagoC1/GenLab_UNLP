"""Seguridad: contraseñas con hash y sesiones con vencimiento.

TODO (tarea 1.4): implementar hash de contraseñas, emisión y validación del token de sesión
y la dependencia `requiere_rol(*roles)`. Por ahora solo está el contrato.
"""

from app.core.enums import Rol


def requiere_rol(*roles: Rol):
    raise NotImplementedError("Pendiente: autenticación y permisos por rol (tarea 1.4)")
