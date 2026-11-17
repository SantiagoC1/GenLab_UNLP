import pytest

from app.core.enums import Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.integrations.cupones import CuponesSimulador, obtener_cupones
from app.main import app
from app.modules.cupones.repositorio import (
    RepositorioCuponesEnMemoria,
    RepositorioMedicosEnMemoria,
    RepositorioPacientesEnMemoria,
    obtener_repositorio,
    obtener_repositorio_medicos,
    obtener_repositorio_pacientes,
)
from tests.fakes import AvisosEspia

ANA = "ana.perez@example.com"
LUCIA = "lucia.fernandez@example.com"


@pytest.fixture
def entorno(client, login_as):
    """Three coupons generated and two of them given to Ana Pérez by the medical manager."""
    integracion_cupones.reiniciar_simulador()
    repositorio = RepositorioCuponesEnMemoria()
    avisos = AvisosEspia()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_repositorio_medicos] = RepositorioMedicosEnMemoria
    app.dependency_overrides[obtener_repositorio_pacientes] = RepositorioPacientesEnMemoria
    app.dependency_overrides[obtener_cupones] = CuponesSimulador
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    login_as(Rol.GERENTE_MEDICO)
    client.post("/cupones/generar", json={"descuento": 20, "cantidad": 3})
    client.post(
        "/cupones/asignar-a-medico",
        json={"contacto_medico": ANA, "codigos": ["CUP-0001", "CUP-0002"]},
    )
    login_as(Rol.MEDICO_TRATANTE, email=ANA)
    yield repositorio, avisos
    integracion_cupones.reiniciar_simulador()


def dar(client, codigo="CUP-0001", paciente=LUCIA):
    return client.post(
        "/cupones/asignar-a-paciente", json={"contacto_paciente": paciente, "codigo": codigo}
    )


def test_el_medico_ve_sus_cupones_disponibles_y_sus_pacientes(client, entorno):
    mis = client.get("/cupones/mis-cupones").json()
    assert mis["cantidad"] == 2
    assert [c["codigo"] for c in mis["cupones"]] == ["CUP-0001", "CUP-0002"]
    pacientes = client.get("/cupones/mis-pacientes").json()
    assert [p["nombre"] for p in pacientes] == ["Lucía Fernández", "Martín Gómez"]


def test_asignar_descuenta_de_los_disponibles_y_lo_publica_para_el_paciente(
    client, entorno, login_as
):
    repositorio, avisos = entorno
    r = dar(client)
    assert r.status_code == 200
    assert r.json()["disponibles"] == 1
    assert r.json()["cupon"]["paciente"] == LUCIA
    assert r.json()["paciente_avisado"] is True
    assert repositorio.obtener("CUP-0001").paciente == LUCIA
    assert client.get("/cupones/mis-cupones").json()["cantidad"] == 1
    assert "20%" in avisos.para(LUCIA)[0]

    login_as(Rol.PACIENTE, email=LUCIA)
    asignados = client.get("/cupones/asignados").json()
    assert [c["codigo"] for c in asignados] == ["CUP-0001"]
    assert asignados[0]["qr"].startswith("data:image/svg+xml")
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    assert client.get("/cupones/asignados").json() == []


def test_sin_cupones_la_asignacion_se_rechaza(client, entorno):
    dar(client, "CUP-0001")
    dar(client, "CUP-0002", paciente="martin.gomez@example.com")
    assert client.get("/cupones/mis-cupones").json()["cantidad"] == 0
    r = dar(client, "CUP-0001")
    assert r.status_code == 409
    assert r.json()["code"] == "sin_cupones"


def test_el_medico_no_puede_dar_un_cupon_que_no_tiene(client, entorno):
    r = dar(client, "CUP-0003")
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_disponible"


def test_el_medico_solo_asigna_a_sus_propios_pacientes(client, entorno):
    r = dar(client, paciente="sofia.ramirez@example.com")
    assert r.status_code == 404
    assert entorno[0].obtener("CUP-0001").paciente is None


def test_un_cupon_que_ya_no_esta_vigente_no_se_asigna(client, entorno):
    CuponesSimulador().marcar_cupon_usado("CUP-0001")
    r = dar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_vigente"


def test_cada_rol_descarga_solo_el_pdf_de_sus_cupones(client, entorno, login_as):
    dar(client)
    assert client.get("/cupones/CUP-0001/pdf").status_code == 200  # the doctor holds it
    assert client.get("/cupones/CUP-0003/pdf").status_code == 404  # not theirs
    login_as(Rol.PACIENTE, email=LUCIA)
    assert client.get("/cupones/CUP-0001/pdf").status_code == 200
    assert client.get("/cupones/CUP-0002/pdf").status_code == 404
    login_as(Rol.GERENTE_MEDICO)
    assert client.get("/cupones/CUP-0003/pdf").status_code == 200
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert client.get("/cupones/CUP-0001/pdf").status_code == 404


def test_los_endpoints_del_medico_exigen_ese_rol(client, entorno, login_as):
    login_as(Rol.PACIENTE, email=LUCIA)
    assert client.get("/cupones/mis-cupones").status_code == 403
    assert dar(client).status_code == 403
    login_as(Rol.MEDICO_TRATANTE, email=ANA)
    assert client.get("/cupones/asignados").status_code == 403
