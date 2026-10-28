"""Pruebas del módulo de acceso (M1) sin conexión a Supabase."""

import pytest

from app.core.config import get_settings
from app.core.errors import AccountBlocked, Unauthenticated
from app.modules.acceso import service, validate
from app.modules.acceso.catalogs import ADMIN_CREATABLE_ROLES, SELF_SIGNUP_ROLES


class FakeUserModel:
    """Reemplaza a app.models.user con un usuario en memoria."""

    def __init__(self, user: dict):
        self.user = user

    def find_by_email(self, email: str):
        return self.user if email == self.user["email"] else None

    def update(self, user_id: str, fields: dict):
        self.user.update(fields)
        return self.user


class FailingAuthClient:
    """Cliente de Auth cuya contraseña o código siempre son incorrectos."""

    def __init__(self):
        self.auth = self

    def sign_in_with_password(self, _credentials):
        raise Exception("invalid login credentials")

    def verify_otp(self, _params):
        raise Exception("invalid code")


@pytest.fixture
def fake_user(monkeypatch) -> dict:
    user = {
        "id": "u1",
        "email": "medico@ejemplo.com",
        "blocked": False,
        "failed_attempts": 0,
    }
    monkeypatch.setattr(service, "user_model", FakeUserModel(user))
    monkeypatch.setattr(service, "new_auth_client", FailingAuthClient)
    return user


def test_users_requires_session(client):
    r = client.get("/acceso/users")
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_session"


def test_login_requires_email_and_password(client):
    r = client.post("/acceso/login", json={})
    assert r.status_code == 422


def test_register_reports_all_missing_fields(client):
    r = client.post("/acceso/register", json={})
    assert r.status_code == 422
    for field in ("role", "first_name", "last_name", "phone", "email", "password"):
        assert f"'{field}'" in r.json()["detalle"]


def test_password_change_validation():
    data = {"current_password": "vieja123", "new_password": "nueva1234", "confirmation": "otra"}
    assert validate.validate_password_change(data) == ["Las contraseñas no coinciden."]
    data["confirmation"] = "nueva1234"
    assert validate.validate_password_change(data) == []


def test_new_password_must_be_long_enough():
    data = {"current_password": "vieja123", "new_password": "corta", "confirmation": "corta"}
    assert len(validate.validate_password_change(data)) == 1


def test_self_signup_cannot_create_carrier():
    data = {
        "role": "transportista",
        "first_name": "A",
        "last_name": "B",
        "phone": "1",
        "email": "",
        "password": "12345678",
    }
    errors = validate.validate_user_data(data, SELF_SIGNUP_ROLES, with_password=True)
    assert "Ese rol no se puede dar de alta por este camino." in errors


def test_admin_cannot_create_patient_or_admin():
    assert "paciente" not in ADMIN_CREATABLE_ROLES
    assert "administrador_general" not in ADMIN_CREATABLE_ROLES


def test_wrong_password_counts_attempts_and_blocks_on_the_limit(fake_user):
    limit = get_settings().max_failed_attempts
    for attempt in range(1, limit):
        with pytest.raises(Unauthenticated):
            service.login_user(fake_user["email"], "incorrecta")
        assert fake_user["failed_attempts"] == attempt
        assert not fake_user["blocked"]

    with pytest.raises(AccountBlocked):
        service.login_user(fake_user["email"], "incorrecta")
    assert fake_user["blocked"]


def test_blocked_account_cannot_log_in(fake_user):
    fake_user["blocked"] = True
    with pytest.raises(AccountBlocked):
        service.login_user(fake_user["email"], "cualquiera")


def test_wrong_code_counts_as_failed_attempt(fake_user):
    with pytest.raises(Unauthenticated):
        service.verify_login_code(fake_user["email"], "000000")
    assert fake_user["failed_attempts"] == 1


def test_unknown_email_gets_the_same_error_as_wrong_password(fake_user):
    with pytest.raises(Unauthenticated) as error:
        service.login_user("otro@ejemplo.com", "x")
    assert str(error.value) == "Credenciales inválidas."