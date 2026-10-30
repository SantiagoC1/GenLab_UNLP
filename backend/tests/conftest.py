import os

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
# Solo para los tests: la clave real de los tokens va en el .env propio
os.environ.setdefault("SECRET_KEY", "clave-solo-para-los-tests-0123456789-abcdef")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.enums import Rol  # noqa: E402
from app.core.security import get_session_user  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def login_as():
    """Simula la sesión de un usuario con ese rol, sin pasar por Supabase.

    REUTILIZABLE: los tests de todos los módulos la usan para probar permisos y rutas
    protegidas. Uso: `login_as(Rol.MEDICO_TRATANTE)`; devuelve el usuario simulado, y se pueden
    pisar sus campos (por ejemplo `must_change_password=True`).
    """

    def _login_as(rol: Rol, **fields) -> dict:
        user = {
            "id": "u-sesion",
            "email": "sesion@ejemplo.com",
            "first_name": "Sesión",
            "last_name": "De prueba",
            "role": rol.value,
            "blocked": False,
            "failed_attempts": 0,
            "must_change_password": False,
            **fields,
        }
        app.dependency_overrides[get_session_user] = lambda: user
        return user

    yield _login_as
    app.dependency_overrides.clear()
