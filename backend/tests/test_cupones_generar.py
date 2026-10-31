import pytest

from app.core.enums import Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.cupones import CuponesError, CuponesSimulador, obtener_cupones
from app.main import app
from app.modules.cupones.repositorio import RepositorioCuponesEnMemoria, obtener_repositorio


class CuponesRechazados(CuponesSimulador):
    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        raise CuponesError("No hay cupos disponibles.")


class CuponesCaido(CuponesSimulador):
    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        raise ConnectionError("sin servicio")


@pytest.fixture
def entorno(login_as):
    integracion_cupones.reiniciar_simulador()
    repositorio = RepositorioCuponesEnMemoria()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_cupones] = CuponesSimulador
    login_as(Rol.GERENTE_MEDICO)
    yield repositorio
    integracion_cupones.reiniciar_simulador()


def test_el_gerente_genera_cupones_vigentes_con_pdf_y_qr(client, entorno):
    r = client.post("/cupones/generar", json={"descuento": 20, "cantidad": 3})
    assert r.status_code == 201
    cupones = r.json()
    assert len(cupones) == 3
    assert {c["estado"] for c in cupones} == {"Vigente"}
    assert {c["descuento"] for c in cupones} == {20}
    assert len({c["codigo"] for c in cupones}) == 3
    assert cupones[0]["qr"].startswith("data:image/svg+xml;base64,")
    assert cupones[0]["pdf_url"] == f"/cupones/{cupones[0]['codigo']}/pdf"
    assert len(entorno.cupones) == 3


def test_dos_generaciones_no_repiten_codigos(client, entorno):
    primero = client.post("/cupones/generar", json={"descuento": 10, "cantidad": 2}).json()
    segundo = client.post("/cupones/generar", json={"descuento": 10, "cantidad": 2}).json()
    codigos = [c["codigo"] for c in primero + segundo]
    assert len(set(codigos)) == 4


def test_el_pdf_del_cupon_se_descarga(client, entorno):
    codigo = client.post("/cupones/generar", json={"descuento": 15, "cantidad": 1}).json()[0][
        "codigo"
    ]
    r = client.get(f"/cupones/{codigo}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert codigo.encode() in r.content
    assert client.get("/cupones/CUP-9999/pdf").status_code == 404


def test_si_el_modulo_de_cupones_rechaza_se_informa_y_no_se_muestra_nada(client, entorno):
    app.dependency_overrides[obtener_cupones] = CuponesRechazados
    r = client.post("/cupones/generar", json={"descuento": 20, "cantidad": 3})
    assert r.status_code == 502
    assert r.json()["code"] == "cupones_rechazados"
    assert "No hay cupos disponibles." in r.json()["detalle"]
    assert entorno.cupones == {}
    assert client.get("/cupones").json() == []


def test_si_el_modulo_de_cupones_no_responde_se_informa_el_error(client, entorno):
    app.dependency_overrides[obtener_cupones] = CuponesCaido
    r = client.post("/cupones/generar", json={"descuento": 20, "cantidad": 3})
    assert r.status_code == 503
    assert entorno.cupones == {}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"descuento": 0, "cantidad": 1},
        {"descuento": 101, "cantidad": 1},
        {"descuento": 10, "cantidad": 0},
        {"descuento": 10, "cantidad": 101},
        {"descuento": 10},
    ],
)
def test_el_descuento_y_la_cantidad_tienen_que_ser_validos(client, entorno, cuerpo):
    assert client.post("/cupones/generar", json=cuerpo).status_code == 422


def test_la_lista_muestra_los_cupones_del_mas_nuevo_al_mas_viejo(client, entorno):
    client.post("/cupones/generar", json={"descuento": 10, "cantidad": 2})
    assert [c["codigo"] for c in client.get("/cupones").json()] == ["CUP-0002", "CUP-0001"]


def test_solo_el_gerente_medico_genera_cupones(client, entorno, login_as):
    login_as(Rol.MEDICO_TRATANTE)
    assert client.post("/cupones/generar", json={"descuento": 10, "cantidad": 1}).status_code == 403
    assert client.get("/cupones").status_code == 403


def test_el_simulador_valida_y_marca_como_usado():
    integracion_cupones.reiniciar_simulador()
    simulador = CuponesSimulador()
    (cupon,) = simulador.obtener_cupones(25, 1)
    assert simulador.validar_cupon(cupon["codigo"])["estado"] == "Vigente"
    assert simulador.marcar_cupon_usado(cupon["codigo"])["estado"] == "Usado"
    assert simulador.validar_cupon(cupon["codigo"])["estado"] == "Usado"
    assert simulador.validar_cupon("CUP-9999")["estado"] == "Inexistente"
    integracion_cupones.reiniciar_simulador()
