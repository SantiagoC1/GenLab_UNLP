import pytest

from app.core.enums import Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.integrations.cupones import CuponesSimulador, obtener_cupones
from app.main import app
from app.modules.cupones.repositorio import (
    RepositorioCuponesEnMemoria,
    RepositorioMedicosEnMemoria,
    obtener_repositorio,
    obtener_repositorio_medicos,
)
from tests.fakes import AvisosCaido, AvisosEspia

ANA = "ana.perez@example.com"


class CuponesCaido(CuponesSimulador):
    def validar_cupon(self, codigo: str) -> dict:
        raise ConnectionError("sin servicio")


@pytest.fixture
def entorno(client, login_as):
    integracion_cupones.reiniciar_simulador()
    repositorio = RepositorioCuponesEnMemoria()
    avisos = AvisosEspia()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_repositorio_medicos] = RepositorioMedicosEnMemoria
    app.dependency_overrides[obtener_cupones] = CuponesSimulador
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    login_as(Rol.GERENTE_MEDICO)
    client.post("/cupones/generar", json={"descuento": 20, "cantidad": 3})
    yield repositorio, avisos
    integracion_cupones.reiniciar_simulador()


def asignar(client, codigos, medico=ANA):
    return client.post(
        "/cupones/asignar-a-medico", json={"contacto_medico": medico, "codigos": codigos}
    )


def test_se_busca_al_medico_por_nombre_o_por_matricula(client, entorno):
    por_nombre = client.get("/cupones/medicos", params={"q": "rivas"}).json()
    assert [m["nombre"] for m in por_nombre] == ["Carlos Rivas"]
    por_matricula = client.get("/cupones/medicos", params={"q": "mp-12345"}).json()
    assert [m["contacto"] for m in por_matricula] == [ANA]
    assert client.get("/cupones/medicos", params={"q": "nadie"}).json() == []
    assert client.get("/cupones/medicos", params={"q": ""}).status_code == 422


def test_se_asignan_uno_o_mas_cupones_vigentes_y_el_medico_recibe_un_aviso(client, entorno):
    repositorio, avisos = entorno
    r = asignar(client, ["CUP-0001", "CUP-0002"])
    assert r.status_code == 200
    assert r.json()["codigos"] == ["CUP-0001", "CUP-0002"]
    assert r.json()["medico"]["nombre"] == "Ana Pérez"
    assert r.json()["medico_avisado"] is True
    assert repositorio.obtener("CUP-0001").medico == ANA
    assert repositorio.obtener("CUP-0003").medico is None
    assert "2 cupones" in avisos.para(ANA)[0]


def test_un_cupon_ya_asignado_no_se_asigna_de_nuevo(client, entorno):
    asignar(client, ["CUP-0001"])
    r = asignar(client, ["CUP-0001"], medico="carlos.rivas@example.com")
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_ya_asignado"


def test_un_cupon_que_no_esta_vigente_no_se_asigna_y_no_se_asigna_ninguno(client, entorno):
    repositorio, avisos = entorno
    CuponesSimulador().marcar_cupon_usado("CUP-0002")
    r = asignar(client, ["CUP-0001", "CUP-0002"])
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_vigente"
    assert repositorio.obtener("CUP-0001").medico is None
    assert avisos.enviados == []


def test_un_cupon_o_un_medico_inexistente_da_404(client, entorno):
    assert asignar(client, ["CUP-9999"]).status_code == 404
    assert asignar(client, ["CUP-0001"], medico="nadie@example.com").status_code == 404


def test_no_se_pueden_repetir_cupones_ni_asignar_una_lista_vacia(client, entorno):
    assert asignar(client, ["CUP-0001", "CUP-0001"]).status_code == 422
    assert asignar(client, []).status_code == 422


def test_si_el_modulo_de_cupones_no_responde_no_se_asigna(client, entorno):
    app.dependency_overrides[obtener_cupones] = CuponesCaido
    r = asignar(client, ["CUP-0001"])
    assert r.status_code == 503
    assert entorno[0].obtener("CUP-0001").medico is None


def test_si_el_aviso_falla_la_asignacion_igual_queda(client, entorno):
    app.dependency_overrides[obtener_avisos] = AvisosCaido
    r = asignar(client, ["CUP-0001"])
    assert r.status_code == 200
    assert r.json()["medico_avisado"] is False
    assert entorno[0].obtener("CUP-0001").medico == ANA


def test_solo_el_gerente_medico_asigna_a_medicos(client, entorno, login_as):
    login_as(Rol.MEDICO_TRATANTE, email=ANA)
    assert asignar(client, ["CUP-0001"]).status_code == 403
    assert client.get("/cupones/medicos", params={"q": "ana"}).status_code == 403
