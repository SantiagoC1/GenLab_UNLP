import pytest

from app.core.enums import Rol
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.main import app
from app.modules.presupuesto_pago import router as router_presupuesto
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)


class AvisosEspia(AvisosIntegracion):
    def __init__(self):
        self.enviados: list[tuple[str, str, str]] = []

    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        self.enviados.append((destinatario, canal, mensaje))
        return True


@pytest.fixture
def avisos():
    espia = AvisosEspia()
    repositorio = RepositorioEstudiosEnMemoria()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_avisos] = lambda: espia
    app.dependency_overrides[router_presupuesto.exigir_administrativo] = lambda: None
    yield espia
    app.dependency_overrides.clear()


def test_la_bandeja_lista_los_estudios_sin_presupuesto(client, avisos):
    r = client.get("/presupuesto_pago/estudios-pendientes")
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [1, 2, 3]
    assert r.json()[1]["cantidad_genes"] == 8


def test_el_detalle_muestra_los_genes_y_el_importe(client, avisos):
    r = client.get("/presupuesto_pago/estudios/2")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["genes"]) == 8
    assert cuerpo["importe_usd"] == 590


def test_el_detalle_de_un_estudio_inexistente_da_404(client, avisos):
    assert client.get("/presupuesto_pago/estudios/99").status_code == 404


def test_emitir_publica_el_presupuesto_y_avisa_al_paciente(client, avisos):
    r = client.post("/presupuesto_pago/estudios/1/presupuesto")
    assert r.status_code == 201
    assert r.json()["importe_usd"] == 500
    assert r.json()["paciente_avisado"] is True
    assert avisos.enviados[0][0] == "lucia.fernandez@example.com"
    ids = [e["id"] for e in client.get("/presupuesto_pago/estudios-pendientes").json()]
    assert ids == [2, 3]


def test_no_se_puede_emitir_dos_veces_el_presupuesto(client, avisos):
    client.post("/presupuesto_pago/estudios/1/presupuesto")
    r = client.post("/presupuesto_pago/estudios/1/presupuesto")
    assert r.status_code == 409
    assert len(avisos.enviados) == 1


def test_el_importe_no_se_puede_editar(client, avisos):
    r = client.post("/presupuesto_pago/estudios/3/presupuesto", json={"importe_usd": 1})
    assert r.json()["importe_usd"] == 500


def test_los_endpoints_exigen_el_rol_administrativo(client, monkeypatch):
    pedidos: list[Rol] = []
    monkeypatch.setattr(router_presupuesto, "requiere_rol", lambda *roles: pedidos.extend(roles))
    app.dependency_overrides[obtener_repositorio] = RepositorioEstudiosEnMemoria
    try:
        client.get("/presupuesto_pago/estudios-pendientes")
    finally:
        app.dependency_overrides.clear()
    assert pedidos == [Rol.ADMINISTRATIVO_LABORATORIO]
