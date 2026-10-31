from datetime import UTC, datetime
from urllib.parse import quote

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations.avisos import obtener_avisos
from app.integrations.obras_sociales import obtener_obras_sociales
from app.main import app
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from tests.fakes import AvisosEspia, ObrasSocialesFalsa

LUCIA = "lucia.fernandez@example.com"
PDF = b"%PDF-1.4 demanda judicial de ejemplo"
HEADERS = {"Content-Type": "application/pdf"}


@pytest.fixture
def entorno(client, login_as):
    """Lucía's study was rejected by OSDE."""
    repositorio = RepositorioEstudiosEnMemoria()
    avisos = AvisosEspia()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[obtener_obras_sociales] = ObrasSocialesFalsa
    repositorio.guardar_presupuesto(1, 500, datetime.now(UTC))
    repositorio.guardar_presupuesto(2, 590, datetime.now(UTC))
    login_as(Rol.PACIENTE, email=LUCIA)
    client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    client.post(
        "/presupuesto_pago/estudios/1/autorizacion",
        json={"resultado": "Rechazado", "motivo": "No cubre estudios genéticos."},
    )
    avisos.enviados.clear()
    login_as(Rol.PACIENTE, email=LUCIA)
    return repositorio, avisos


def enviar(client, contenido=PDF, estudio=1, headers=None):
    return client.post(
        f"/presupuesto_pago/mis-estudios/{estudio}/demanda",
        content=contenido,
        headers=headers or HEADERS,
    )


def test_el_paciente_ve_el_motivo_del_rechazo(client, entorno):
    estudio = client.get("/presupuesto_pago/mis-estudios").json()[0]
    assert estudio["estado"] == "Rechazado"
    assert estudio["cobertura"]["motivo_rechazo"] == "No cubre estudios genéticos."
    assert estudio["cobertura"]["demanda_enviada"] is False


def test_adjuntar_la_demanda_la_asocia_al_estudio_y_avisa_al_administrativo(client, entorno):
    repositorio, avisos = entorno
    r = enviar(client, headers=HEADERS | {"X-Nombre-Archivo": quote("fallo judicial.pdf")})
    assert r.status_code == 201
    assert r.json()["demanda_nombre"] == "fallo judicial.pdf"
    assert r.json()["administrativo_avisado"] is True
    assert r.json()["estado"] == "Rechazado"  # stays Rechazado until the new answer
    assert repositorio.obtener(1).cobertura.demanda == PDF
    assert "reautorización" in avisos.enviados[0][2]
    assert client.get("/presupuesto_pago/mis-estudios").json()[0]["cobertura"]["demanda_enviada"]


@pytest.mark.parametrize(
    "contenido",
    [b"esto es un texto", b"\x89PNG\r\n\x1a\n imagen", b"<html>%PDF-</html>"],
)
def test_un_archivo_que_no_es_pdf_se_rechaza(client, entorno, contenido):
    r = enviar(client, contenido)
    assert r.status_code == 422
    assert r.json()["code"] == "archivo_no_pdf"
    assert entorno[0].obtener(1).cobertura.demanda is None


def test_un_archivo_vacio_o_demasiado_grande_se_rechaza(client, entorno):
    assert enviar(client, b"").status_code == 422
    assert enviar(client, b"%PDF-" + b"0" * (5 * 1024 * 1024)).status_code == 413


def test_solo_se_adjunta_la_demanda_de_un_estudio_rechazado(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    r = enviar(client, estudio=2)
    assert r.status_code == 409
    assert r.json()["code"] == "estudio_no_rechazado"


def test_no_se_envia_dos_demandas_a_la_vez(client, entorno):
    enviar(client)
    r = enviar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "demanda_ya_enviada"


def test_el_estudio_de_otro_paciente_da_404(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    assert enviar(client).status_code == 404


def test_el_administrativo_descarga_la_demanda_y_registra_la_nueva_respuesta(
    client, entorno, login_as
):
    repositorio, avisos = entorno
    enviar(client)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)

    pendientes = client.get("/presupuesto_pago/autorizaciones-pendientes").json()
    assert [(p["estudio_id"], p["con_demanda"], p["estado_estudio"]) for p in pendientes] == [
        (1, True, "Rechazado")
    ]
    assert pendientes[0]["motivo_rechazo"] == "No cubre estudios genéticos."

    descarga = client.get("/presupuesto_pago/estudios/1/demanda")
    assert descarga.status_code == 200
    assert descarga.headers["content-type"] == "application/pdf"
    assert descarga.content == PDF

    r = client.post("/presupuesto_pago/estudios/1/autorizacion", json={"resultado": "Autorizado"})
    assert r.status_code == 200
    assert r.json()["estado"] == "Autorizado"
    assert repositorio.obtener(1).estado == EstadoEstudio.AUTORIZADO
    assert len(repositorio.asientos) == 1
    assert client.get("/presupuesto_pago/autorizaciones-pendientes").json() == []
    assert client.get("/presupuesto_pago/estudios/1/demanda").status_code == 404


def test_si_la_obra_social_rechaza_de_nuevo_el_paciente_puede_adjuntar_otra_demanda(
    client, entorno, login_as
):
    repositorio, _ = entorno
    enviar(client)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    r = client.post(
        "/presupuesto_pago/estudios/1/autorizacion",
        json={"resultado": "Rechazado", "motivo": "Apelación en trámite."},
    )
    assert r.status_code == 200
    assert repositorio.obtener(1).estado == EstadoEstudio.RECHAZADO
    assert repositorio.obtener(1).cobertura.motivo_rechazo == "Apelación en trámite."
    assert client.get("/presupuesto_pago/autorizaciones-pendientes").json() == []

    login_as(Rol.PACIENTE, email=LUCIA)
    assert enviar(client).status_code == 201


def test_sin_demanda_un_estudio_rechazado_no_espera_respuesta(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert client.get("/presupuesto_pago/autorizaciones-pendientes").json() == []
    r = client.post("/presupuesto_pago/estudios/1/autorizacion", json={"resultado": "Autorizado"})
    assert r.status_code == 409


def test_los_permisos_de_la_demanda(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert enviar(client).status_code == 403
    login_as(Rol.PACIENTE, email=LUCIA)
    enviar(client)
    assert client.get("/presupuesto_pago/estudios/1/demanda").status_code == 403
