import pytest
from starlette.requests import Request

from app import dev_demo
from app.core import dev_auth
from app.core.config import Settings, get_settings
from app.core.dev_auth import ROLE_HEADER, USER_HEADER
from app.main import app
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)

TRAY = "/presupuesto_pago/estudios-pendientes"


@pytest.fixture
def estudios():
    repositorio = RepositorioEstudiosEnMemoria()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    yield repositorio
    app.dependency_overrides.clear()


@pytest.fixture
def dev_auth_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "dev_auth", True)


def con_rol(rol, usuario=None):
    headers = {ROLE_HEADER: rol}
    if usuario:
        headers[USER_HEADER] = usuario
    return headers


# --- off by default -------------------------------------------------------------------------


def test_por_defecto_esta_apagado(monkeypatch):
    monkeypatch.delenv("DEV_AUTH", raising=False)
    assert Settings(_env_file=None).dev_auth is False


@pytest.mark.parametrize("valor", ["false", "False", "0"])
def test_con_false_queda_apagado(monkeypatch, valor):
    monkeypatch.setenv("DEV_AUTH", valor)
    assert Settings(_env_file=None).dev_auth is False


def test_con_true_se_enciende(monkeypatch):
    monkeypatch.setenv("DEV_AUTH", "true")
    assert Settings(_env_file=None).dev_auth is True


def test_apagado_el_encabezado_se_ignora(client, estudios):
    assert get_settings().dev_auth is False
    r = client.get(TRAY, headers=con_rol("administrativo_laboratorio"))
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_session"


def test_apagado_no_se_cargan_datos_de_demostracion(monkeypatch, estudios):
    monkeypatch.setattr(dev_demo, "obtener_repositorio", lambda: estudios)
    assert dev_demo.seed_demo() is False
    assert not estudios.obtener(1).tiene_presupuesto


# --- on --------------------------------------------------------------------------------------


def test_encendido_el_encabezado_arma_la_sesion_con_ese_rol(client, estudios, dev_auth_on):
    assert client.get(TRAY, headers=con_rol("administrativo_laboratorio")).status_code == 200


def test_encendido_el_rol_se_respeta_y_los_permisos_siguen_valiendo(client, estudios, dev_auth_on):
    r = client.get(TRAY, headers=con_rol("paciente"))
    assert r.status_code == 403


def test_encendido_sin_encabezado_o_con_un_rol_inventado_sigue_el_401(
    client, estudios, dev_auth_on
):
    assert client.get(TRAY).status_code == 401
    assert client.get(TRAY, headers=con_rol("superusuario")).status_code == 401


def pedido(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def test_encendido_el_paciente_y_el_medico_usan_las_cuentas_de_la_demostracion(dev_auth_on):
    paciente = dev_auth.user_from_request(pedido(con_rol("paciente")))
    medico = dev_auth.user_from_request(pedido(con_rol("medico_tratante")))
    assert paciente["email"] == "lucia.fernandez@example.com"
    assert paciente["role"] == "paciente"
    assert medico["email"] == "ana.perez@example.com"


def test_el_resto_de_los_roles_tiene_una_cuenta_propia(dev_auth_on):
    usuario = dev_auth.user_from_request(pedido(con_rol("transportista")))
    assert usuario["email"] == "dev-transportista@example.com"
    assert usuario["must_change_password"] is False and usuario["blocked"] is False


def test_x_dev_user_cambia_la_cuenta_de_la_sesion(dev_auth_on):
    usuario = dev_auth.user_from_request(pedido(con_rol("paciente", "martin.gomez@example.com")))
    assert usuario["email"] == "martin.gomez@example.com"
    assert usuario["role"] == "paciente"


def test_apagado_el_pedido_no_arma_ninguna_sesion():
    assert dev_auth.user_from_request(pedido(con_rol("paciente"))) is None


def test_encendido_carga_los_datos_de_demostracion(monkeypatch, estudios, dev_auth_on):
    monkeypatch.setattr(dev_demo, "obtener_repositorio", lambda: estudios)
    assert dev_demo.seed_demo() is True
    assert estudios.obtener(1).presupuesto_importe_usd == 500
    assert estudios.obtener(2).presupuesto_importe_usd == 590
    assert not estudios.obtener(3).tiene_presupuesto  # still in the administrative tray
    dev_demo.seed_demo()  # running it twice changes nothing
    assert estudios.obtener(1).presupuesto_importe_usd == 500


def test_apagar_de_nuevo_vuelve_a_pedir_la_sesion(client, estudios, monkeypatch):
    monkeypatch.setattr(get_settings(), "dev_auth", True)
    assert client.get(TRAY, headers=con_rol("administrativo_laboratorio")).status_code == 200
    monkeypatch.setattr(get_settings(), "dev_auth", False)
    assert client.get(TRAY, headers=con_rol("administrativo_laboratorio")).status_code == 401
