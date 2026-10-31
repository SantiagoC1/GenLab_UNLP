from datetime import UTC, datetime

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.core.errors import BusinessRuleError
from app.integrations.obras_sociales import obtener_obras_sociales
from app.main import app
from app.modules.presupuesto_pago.estado import TRANSITIONS, validate_transition
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from tests.fakes import ObrasSocialesFalsa

PACIENTE = "lucia.fernandez@example.com"


class ObrasSocialesCaida(ObrasSocialesFalsa):
    def listar_obras_sociales(self) -> list[dict]:
        raise ConnectionError("sin servicio")


@pytest.fixture
def entorno(login_as):
    repositorio = RepositorioEstudiosEnMemoria()
    obras = ObrasSocialesFalsa()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_obras_sociales] = lambda: obras
    login_as(Rol.PACIENTE, email=PACIENTE)
    repositorio.guardar_presupuesto(1, 500, datetime.now(UTC))
    yield repositorio, obras


def test_el_paciente_ve_la_lista_de_obras_sociales_con_su_cobertura(client, entorno):
    r = client.get("/presupuesto_pago/obras-sociales")
    assert r.status_code == 200
    assert r.json() == [
        {"nombre": "OSDE", "cobertura": 80},
        {"nombre": "Swiss Medical", "cobertura": 60},
    ]


def test_el_paciente_solo_ve_sus_estudios(client, entorno):
    r = client.get("/presupuesto_pago/mis-estudios")
    assert [e["id"] for e in r.json()] == [1]
    assert r.json()[0]["importe_usd"] == 500
    assert r.json()[0]["cobertura"] is None


def test_elegir_la_cobertura_deja_el_estudio_a_la_espera_de_la_autorizacion(client, entorno):
    repositorio, obras = entorno
    r = client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    assert r.status_code == 201
    assert r.json()["cobertura"] == {
        "obra_social": "OSDE",
        "porcentaje": 80,
        "estado": "Pendiente",
        "motivo_rechazo": None,
    }
    # does not advance until the administrative user answers
    assert r.json()["estado"] == "Creado"
    assert repositorio.obtener(1).estado == EstadoEstudio.CREADO
    assert obras.altas[0][0] == "Estudio 1 - Lucía Fernández"


def test_una_obra_social_que_no_figura_en_la_lista_solo_deja_el_pago_particular(client, entorno):
    r = client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "Otra"})
    assert r.status_code == 409
    assert r.json()["code"] == "obra_social_no_listada"
    assert "particular" in r.json()["detalle"]
    assert entorno[0].obtener(1).cobertura is None


def test_no_se_elige_la_cobertura_sin_presupuesto(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    r = client.post("/presupuesto_pago/mis-estudios/2/cobertura", json={"obra_social": "OSDE"})
    assert r.status_code == 409


def test_no_se_elige_dos_veces_la_cobertura(client, entorno):
    client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    r = client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    assert r.status_code == 409
    assert r.json()["code"] == "cobertura_ya_elegida"


def test_un_paciente_no_puede_tocar_el_estudio_de_otro(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    r = client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    assert r.status_code == 404


def test_si_el_modulo_de_obras_sociales_cae_se_informa_el_error(client, entorno):
    app.dependency_overrides[obtener_obras_sociales] = ObrasSocialesCaida
    r = client.get("/presupuesto_pago/obras-sociales")
    assert r.status_code == 503
    r = client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    assert r.status_code == 503
    assert entorno[0].obtener(1).cobertura is None


def test_los_endpoints_del_paciente_exigen_ese_rol(client, entorno, login_as):
    login_as(Rol.MEDICO_TRATANTE)
    assert client.get("/presupuesto_pago/mis-estudios").status_code == 403
    assert client.get("/presupuesto_pago/obras-sociales").status_code == 403


# --- study state model --------------------------------------------------------------------


def test_todo_estado_tiene_sus_transiciones_definidas():
    assert set(TRANSITIONS) == set(EstadoEstudio)


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoEstudio.CREADO, EstadoEstudio.TURNO_SACADO),
        (EstadoEstudio.CREADO, EstadoEstudio.LISTO_PARA_RETIRAR),
        (EstadoEstudio.RECHAZADO, EstadoEstudio.PAGADO),
        (EstadoEstudio.PAGADO, EstadoEstudio.AUTORIZADO),
        (EstadoEstudio.RESULTADO_DISPONIBLE, EstadoEstudio.CREADO),
    ],
)
def test_una_transicion_invalida_se_rechaza(desde, hacia):
    with pytest.raises(BusinessRuleError):
        validate_transition(desde, hacia)


def test_cambiar_el_estado_deja_el_historial():
    repositorio = RepositorioEstudiosEnMemoria()
    ahora = datetime.now(UTC)
    repositorio.cambiar_estado(1, EstadoEstudio.PAGADO, ahora)
    estudio = repositorio.obtener(1)
    assert estudio.estado == EstadoEstudio.PAGADO
    assert [(c.desde, c.hacia) for c in estudio.historial] == [
        (EstadoEstudio.CREADO, EstadoEstudio.PAGADO)
    ]
    with pytest.raises(BusinessRuleError):
        repositorio.cambiar_estado(1, EstadoEstudio.CREADO, ahora)
