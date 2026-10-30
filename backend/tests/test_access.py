"""Pruebas del módulo de acceso (M1) sin conexión a Supabase."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from supabase import AuthApiError, PostgrestAPIError

from app.core.config import get_settings
from app.core.enums import Rol
from app.core.errors import (
    AccountBlocked,
    BusinessRuleError,
    InvalidIntegration,
    TooManyRequests,
    Unauthenticated,
)
from app.core.security import (
    CHALLENGE,
    SESSION,
    create_session_token,
    create_token,
    decode_token,
)
from app.models import user as user_model_module
from app.modules.acceso import service, validate
from app.modules.acceso.catalogs import ADMIN_CREATABLE_ROLES, SELF_SIGNUP_ROLES


class FakeUserModel:
    """Reemplaza a app.models.user con un usuario en memoria."""

    def __init__(self, user: dict):
        self.user = user

    def find_by_email(self, email: str):
        return self.user if email == self.user["email"] else None

    def find_by_id(self, user_id: str):
        return self.user if user_id == self.user["id"] else None

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
    for label in ("rol", "nombre", "apellido", "teléfono", "mail", "contraseña"):
        assert f"'{label}'" in r.json()["detalle"]
    assert "first_name" not in r.json()["detalle"]


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
    challenge = create_token("u1", CHALLENGE, 10, dev=None)
    with pytest.raises(Unauthenticated):
        service.verify_login_code(fake_user["email"], "000000", challenge)
    assert fake_user["failed_attempts"] == 1


def test_unknown_email_gets_the_same_error_as_wrong_password(fake_user):
    with pytest.raises(Unauthenticated) as error:
        service.login_user("otro@ejemplo.com", "x")
    assert str(error.value) == "Credenciales inválidas."


# --- Validaciones del ingreso y mensajes en español ---


def test_login_and_code_validation():
    assert validate.validate_login({"email": "a@b.com", "password": "x"}) == []
    assert validate.validate_login({"email": "a@b.com"}) == ["Completá el mail y la contraseña."]
    complete = {"email": "a@b.com", "code": "123456", "challenge": "token"}
    assert validate.validate_code(complete) == []
    assert validate.validate_code({**complete, "email": None}) == ["Completá el mail y el código."]
    assert validate.validate_code({**complete, "challenge": None}) == [
        "Volvé a ingresar con tu contraseña para recibir un código."
    ]


def test_password_change_reports_missing_fields_in_spanish():
    errors = validate.validate_password_change({})
    assert "El campo 'contraseña actual' es obligatorio." in errors
    assert "El campo 'contraseña nueva' es obligatorio." in errors


# --- Permisos y sesión (usan login_as) ---


def test_users_list_is_forbidden_for_other_roles(client, login_as):
    login_as(Rol.PACIENTE)
    r = client.get("/acceso/users")
    assert r.status_code == 403


def test_admin_can_list_users(client, login_as, monkeypatch):
    login_as(Rol.ADMINISTRADOR_GENERAL)
    monkeypatch.setattr(service, "list_users", lambda: [])
    r = client.get("/acceso/users")
    assert r.status_code == 200
    assert r.json() == []


def test_user_with_initial_password_cannot_use_other_routes(client, login_as):
    login_as(Rol.ADMINISTRADOR_GENERAL, must_change_password=True)
    r = client.get("/acceso/users")
    assert r.status_code == 403
    assert r.json()["code"] == "must_change_password"


USER_ID = "00000000-0000-0000-0000-000000000009"


def test_unblock_rejects_an_id_that_is_not_a_uuid(client, login_as):
    login_as(Rol.ADMINISTRADOR_GENERAL)
    assert client.post("/acceso/users/no-es-un-uuid/unblock").status_code == 422


def test_only_admin_can_unblock(client, login_as, monkeypatch):
    monkeypatch.setattr(service, "unblock_user", lambda user_id: {"id": user_id, "blocked": False})
    login_as(Rol.GERENTE_MEDICO)
    assert client.post(f"/acceso/users/{USER_ID}/unblock").status_code == 403

    login_as(Rol.ADMINISTRADOR_GENERAL)
    r = client.post(f"/acceso/users/{USER_ID}/unblock")
    assert r.status_code == 200
    assert r.json() == {"id": USER_ID, "blocked": False}


# --- Desbloqueo ---


@pytest.fixture
def blocked_user(monkeypatch) -> dict:
    user = {
        "id": "u1",
        "email": "medico@ejemplo.com",
        "first_name": "A",
        "last_name": "B",
        "phone": "1",
        "role": "medico_tratante",
        "province": None,
        "license_number": "123",
        "blocked": True,
        "failed_attempts": 5,
    }
    monkeypatch.setattr(service, "user_model", FakeUserModel(user))
    return user


def test_unblock_resets_the_account(blocked_user):
    result = service.unblock_user("u1")
    assert result["blocked"] is False
    assert blocked_user["failed_attempts"] == 0


def test_unblock_unknown_user_is_404(blocked_user):
    with pytest.raises(BusinessRuleError) as error:
        service.unblock_user("no-existe")
    assert error.value.status_code == 404


# --- Cambio de contraseña ---


class AcceptingAuthClient:
    """Cliente de Auth que acepta la contraseña."""

    def __init__(self):
        self.auth = self

    def sign_in_with_password(self, _credentials):
        return None


class FakeAdminAuth:
    """Reemplaza a `supabase_admin`: registra las altas y bajas de usuarios de Auth."""

    def __init__(self, create_error: Exception | None = None):
        self.create_error = create_error
        self.created: list[dict] = []
        self.deleted: list[str] = []
        self.passwords: dict[str, str] = {}
        self.auth = SimpleNamespace(admin=self)

    def create_user(self, attributes: dict):
        if self.create_error:
            raise self.create_error
        self.created.append(attributes)
        return SimpleNamespace(user=SimpleNamespace(id="auth-1"))

    def delete_user(self, user_id: str):
        self.deleted.append(user_id)

    def update_user_by_id(self, user_id: str, attributes: dict):
        self.passwords[user_id] = attributes["password"]


def test_wrong_current_password_counts_as_failed_attempt(fake_user):
    with pytest.raises(Unauthenticated):
        service.change_password(fake_user, "incorrecta", "nueva-clave-1")
    assert fake_user["failed_attempts"] == 1


def test_new_password_must_differ_from_current(fake_user, monkeypatch):
    monkeypatch.setattr(service, "new_auth_client", AcceptingAuthClient)
    with pytest.raises(BusinessRuleError) as error:
        service.change_password(fake_user, "misma-clave-1", "misma-clave-1")
    assert error.value.status_code == 422


def test_password_change_clears_the_initial_password_flag(fake_user, monkeypatch):
    admin = FakeAdminAuth()
    monkeypatch.setattr(service, "new_auth_client", AcceptingAuthClient)
    monkeypatch.setattr(service, "supabase_admin", admin)
    fake_user["must_change_password"] = True
    fake_user["failed_attempts"] = 3

    service.change_password(fake_user, "vieja-clave-1", "nueva-clave-1")

    assert admin.passwords == {"u1": "nueva-clave-1"}
    assert fake_user["must_change_password"] is False
    assert fake_user["failed_attempts"] == 0


# --- Reenvío del código ---


class OtpAuthClient:
    """Cliente de Auth con contraseña correcta y un error configurable al enviar el código."""

    error: Exception | None = None

    def __init__(self):
        self.auth = self

    def sign_in_with_password(self, _credentials):
        return None

    def sign_in_with_otp(self, _params):
        if self.error:
            raise self.error


def test_resending_the_code_too_soon_is_a_429(fake_user, monkeypatch):
    OtpAuthClient.error = AuthApiError("rate limit", 429, "over_email_send_rate_limit")
    monkeypatch.setattr(service, "new_auth_client", OtpAuthClient)
    with pytest.raises(TooManyRequests) as error:
        service.login_user(fake_user["email"], "clave")
    assert error.value.status_code == 429
    assert fake_user["failed_attempts"] == 0


def test_other_mail_failures_are_an_unavailable_integration(fake_user, monkeypatch):
    OtpAuthClient.error = Exception("smtp caído")
    monkeypatch.setattr(service, "new_auth_client", OtpAuthClient)
    with pytest.raises(InvalidIntegration):
        service.login_user(fake_user["email"], "clave")


# --- Alta de usuarios ---


class RecordingUserModel:
    """Reemplaza a `app.models.user` en el alta: guarda lo que se le pide crear."""

    def __init__(self, create_error: Exception | None = None):
        self.create_error = create_error
        self.rows: list[dict] = []
        self.deleted: list[str] = []

    def create(self, row: dict):
        if self.create_error:
            raise self.create_error
        self.rows.append(row)
        return row

    def delete(self, user_id: str):
        self.deleted.append(user_id)


PERSON = {
    "email": "  Lucia@Ejemplo.COM ",
    "first_name": " Lucía ",
    "last_name": "Pérez",
    "phone": "221",
}


def test_create_account_normalizes_data_and_flags_the_initial_password(monkeypatch):
    admin, users = FakeAdminAuth(), RecordingUserModel()
    monkeypatch.setattr(service, "supabase_admin", admin)
    monkeypatch.setattr(service, "user_model", users)

    service.create_account({**PERSON, "role": "paciente"}, "temporal-1", True)

    assert admin.created[0]["email"] == "lucia@ejemplo.com"
    row = users.rows[0]
    assert row["first_name"] == "Lucía"
    assert row["must_change_password"] is True


def test_create_account_only_keeps_the_fields_of_the_role(monkeypatch):
    users = RecordingUserModel()
    monkeypatch.setattr(service, "supabase_admin", FakeAdminAuth())
    monkeypatch.setattr(service, "user_model", users)
    extra = {"province": "Córdoba", "license_number": "99", "specialties": [1]}

    service.create_account({**PERSON, **extra, "role": "bioinformatico"}, "x", False)
    service.create_account({**PERSON, **extra, "role": "medico_tratante"}, "x", False)
    service.create_account({**PERSON, **extra, "role": "transportista"}, "x", False)

    other, doctor, carrier = users.rows
    assert (other["province"], other["license_number"], other["specialty_ids"]) == (None, None, [])
    assert (doctor["province"], doctor["license_number"], doctor["specialty_ids"]) == (
        None,
        "99",
        [1],
    )
    assert (carrier["province"], carrier["license_number"]) == ("Córdoba", None)


def test_create_account_with_an_existing_mail_is_a_422(monkeypatch):
    error = AuthApiError("exists", 422, "email_exists")
    monkeypatch.setattr(service, "supabase_admin", FakeAdminAuth(create_error=error))
    with pytest.raises(BusinessRuleError) as raised:
        service.create_account({**PERSON, "role": "paciente"}, "x", False)
    assert raised.value.message == "Ya existe un usuario con ese mail."


def test_create_account_with_data_rejected_by_auth_is_a_422(monkeypatch):
    error = AuthApiError("weak", 422, "weak_password")
    monkeypatch.setattr(service, "supabase_admin", FakeAdminAuth(create_error=error))
    with pytest.raises(BusinessRuleError) as raised:
        service.create_account({**PERSON, "role": "paciente"}, "x", False)
    assert raised.value.status_code == 422


def test_create_account_does_not_hide_an_auth_server_failure(monkeypatch):
    error = AuthApiError("caído", 500, None)
    monkeypatch.setattr(service, "supabase_admin", FakeAdminAuth(create_error=error))
    with pytest.raises(AuthApiError):
        service.create_account({**PERSON, "role": "paciente"}, "x", False)


def test_second_carrier_for_a_province_is_a_422_and_undoes_the_auth_user(monkeypatch):
    duplicate = PostgrestAPIError(
        {
            "code": "23505",
            "message": "duplicate key value violates unique constraint",
            "details": "Key (province)=(Córdoba) already exists.",
        }
    )
    admin = FakeAdminAuth()
    monkeypatch.setattr(service, "supabase_admin", admin)
    monkeypatch.setattr(service, "user_model", RecordingUserModel(create_error=duplicate))

    with pytest.raises(BusinessRuleError) as raised:
        data = {**PERSON, "role": "transportista", "province": "Córdoba"}
        service.create_account(data, "x", False)

    assert raised.value.message == "Ya hay un transportista para Córdoba."
    assert raised.value.status_code == 422
    assert admin.deleted == ["auth-1"]


def test_admin_signup_is_undone_if_the_mail_does_not_go_out(monkeypatch):
    admin, users = FakeAdminAuth(), RecordingUserModel()
    monkeypatch.setattr(service, "supabase_admin", admin)
    monkeypatch.setattr(service, "user_model", users)
    monkeypatch.setattr(
        service, "obtener_avisos", lambda: SimpleNamespace(enviar_aviso=lambda *args: False)
    )
    creator = {"first_name": "Ana", "last_name": "Gómez"}

    with pytest.raises(InvalidIntegration):
        service.create_user_as_admin({**PERSON, "role": "bioinformatico", "id": "x"}, creator)

    assert users.deleted == ["auth-1"]
    assert admin.deleted == ["auth-1"]


# --- Tokens propios (JWT) ---

OTHER_KEY = "otra-clave-que-no-es-la-nuestra-0123456789"


def _forged(key, **claims) -> str:
    payload = {"sub": "a1", "typ": SESSION, "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return jwt.encode({**payload, **claims}, key, algorithm="HS256" if key else "none")


def test_session_token_round_trip():
    claims = decode_token(create_session_token("u1"), SESSION)
    assert claims["sub"] == "u1"


def test_expired_token_is_rejected():
    token = create_token("u1", SESSION, expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, SESSION)


def test_token_of_another_kind_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(create_token("u1", CHALLENGE, 5), SESSION)


def test_token_signed_with_another_key_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(_forged(OTHER_KEY), SESSION)


def test_unsigned_token_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(_forged(None), SESSION)


def test_a_short_secret_signs_nothing(monkeypatch):
    monkeypatch.setattr(get_settings(), "secret_key", "corta")
    with pytest.raises(RuntimeError):
        create_session_token("u1")


@pytest.fixture
def stored_admin(monkeypatch) -> dict:
    admin = {
        "id": "a1",
        "role": "administrador_general",
        "blocked": False,
        "must_change_password": False,
    }
    monkeypatch.setattr(user_model_module, "find_by_id", lambda uid: admin if uid == "a1" else None)
    monkeypatch.setattr(service, "list_users", lambda: [])
    return admin


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_valid_session_token_opens_the_session(client, stored_admin):
    r = client.get("/acceso/users", headers=_bearer(create_session_token("a1")))
    assert r.status_code == 200


def test_verification_token_does_not_open_a_session(client, stored_admin):
    r = client.get("/acceso/users", headers=_bearer(create_token("a1", CHALLENGE, 5)))
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_session"


def test_token_from_the_auth_provider_does_not_open_a_session(client, stored_admin):
    forged = _forged(OTHER_KEY, aud="authenticated", role="authenticated")
    r = client.get("/acceso/users", headers=_bearer(forged))
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_session"


def test_session_of_a_blocked_user_is_rejected(client, stored_admin):
    stored_admin["blocked"] = True
    r = client.get("/acceso/users", headers=_bearer(create_session_token("a1")))
    assert r.status_code == 401


# --- Ingreso: dispositivo nuevo o de confianza ---


class FakeTrustedDevices:
    """Reemplaza a `app.models.trusted_device` con un conjunto en memoria."""

    def __init__(self):
        self.devices: set[tuple[str, str]] = set()

    def exists(self, user_id: str, device_hash: str) -> bool:
        return (user_id, device_hash) in self.devices

    def add(self, user_id: str, device_hash: str) -> None:
        self.devices.add((user_id, device_hash))


class CodeAuthClient(OtpAuthClient):
    """Cliente de Auth con contraseña y código correctos."""

    def verify_otp(self, _params):
        return None


@pytest.fixture
def devices(monkeypatch) -> FakeTrustedDevices:
    fake = FakeTrustedDevices()
    monkeypatch.setattr(service, "trusted_device_model", fake)
    return fake


@pytest.fixture
def accepting_user(fake_user, monkeypatch) -> dict:
    CodeAuthClient.error = None
    monkeypatch.setattr(service, "new_auth_client", CodeAuthClient)
    return fake_user


def test_new_device_gets_a_code_and_a_verification_token(accepting_user, devices):
    result = service.login_user(accepting_user["email"], "clave", "device-1")

    assert result["state"] == "code_sent"
    claims = decode_token(result["challenge"], CHALLENGE)
    assert claims["sub"] == "u1"
    assert claims["dev"] == service._hash_device("device-1")
    assert claims["dev"] != "device-1"  # nunca viaja el identificador original


def test_trusted_device_enters_without_a_code(accepting_user, devices, monkeypatch):
    devices.add("u1", service._hash_device("device-1"))
    CodeAuthClient.error = Exception("no se debería mandar ningún código")
    accepting_user["failed_attempts"] = 2

    result = service.login_user(accepting_user["email"], "clave", "device-1")

    assert result["state"] == "authenticated"
    assert decode_token(result["token"], SESSION)["sub"] == "u1"
    assert accepting_user["failed_attempts"] == 0


def test_trust_is_per_device(accepting_user, devices):
    devices.add("u1", service._hash_device("device-1"))
    result = service.login_user(accepting_user["email"], "clave", "device-2")
    assert result["state"] == "code_sent"


def test_without_a_device_id_a_code_is_always_asked(accepting_user, devices):
    result = service.login_user(accepting_user["email"], "clave")
    assert result["state"] == "code_sent"
    assert decode_token(result["challenge"], CHALLENGE)["dev"] is None


def test_right_code_opens_the_session_and_trusts_the_device(accepting_user, devices):
    challenge = service.login_user(accepting_user["email"], "clave", "device-1")["challenge"]

    token, user = service.verify_login_code(
        accepting_user["email"], "123456", challenge, "device-1"
    )

    assert decode_token(token, SESSION)["sub"] == "u1"
    assert user["id"] == "u1"
    assert devices.exists("u1", service._hash_device("device-1"))


def test_code_without_the_password_step_is_not_enough(accepting_user, devices):
    for challenge in ("", "basura", create_token("u1", CHALLENGE, expires_minutes=-1)):
        with pytest.raises(Unauthenticated):
            service.verify_login_code(accepting_user["email"], "123456", challenge, "device-1")
    assert accepting_user["failed_attempts"] == 0  # sin la contraseña no se cuentan intentos
    assert not devices.devices


def test_verification_token_is_tied_to_the_device_and_the_user(accepting_user, devices):
    challenge = service.login_user(accepting_user["email"], "clave", "device-1")["challenge"]
    with pytest.raises(Unauthenticated):
        service.verify_login_code(accepting_user["email"], "123456", challenge, "device-2")

    other = create_token("otro-usuario", CHALLENGE, 10, dev=service._hash_device("device-1"))
    with pytest.raises(Unauthenticated):
        service.verify_login_code(accepting_user["email"], "123456", other, "device-1")
    assert not devices.devices


def test_register_opens_a_session_with_our_own_token(monkeypatch):
    created = {"id": "n1", "email": "nuevo@ejemplo.com"}
    monkeypatch.setattr(service, "create_account", lambda *args, **kwargs: created)

    token, user = service.register_user({"password": "una-clave-larga"})

    assert decode_token(token, SESSION)["sub"] == "n1"
    assert user is created
