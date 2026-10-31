import re
from datetime import datetime

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations.avisos import obtener_avisos
from app.main import app
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from app.modules.turnos import reglas
from app.modules.turnos.reglas import ARG
from app.modules.turnos.repositorio import CANCELADO, RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)


def texto_del_pdf(contenido: bytes) -> str:
    """The text lines of the PDF, joined with spaces (long paragraphs are wrapped)."""
    lineas = re.findall(rb"\((.*?)\) Tj", contenido)
    return " ".join(linea.decode("cp1252") for linea in lineas)


@pytest.fixture
def entorno(client, login_as):
    """Lucía has a Pagado study and an appointment on Tuesday 3 November at 9:15."""
    estudios = RepositorioEstudiosEnMemoria()
    turnos = RepositorioTurnosEnMemoria()
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, AHORA)
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: turnos
    app.dependency_overrides[obtener_avisos] = AvisosEspia
    app.dependency_overrides[reglas.ahora] = lambda: AHORA
    login_as(Rol.PACIENTE, email=LUCIA)
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": INICIO.isoformat()},
    )
    assert r.status_code == 201
    return estudios, turnos, r.json()


def test_la_reserva_publica_los_enlaces_de_los_documentos(client, entorno):
    _, _, turno = entorno
    assert turno["orden_extraccion_url"] == f"/turnos/{turno['id']}/orden-extraccion"
    assert turno["consentimiento_url"] == f"/turnos/{turno['id']}/consentimiento-informado"


def test_la_orden_de_extraccion_tiene_fecha_hora_laboratorio_e_indicaciones(client, entorno):
    r = client.get("/turnos/1/orden-extraccion")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    texto = texto_del_pdf(r.content)
    assert "Orden de extracción" in texto
    assert "Paciente: Lucía Fernández" in texto
    assert "Fecha: 03/11/2026" in texto
    assert "Hora: 09:15" in texto
    assert "Laboratorio de extracción: Laboratorio de extracción Buenos Aires 1" in texto
    assert "Indicaciones" in texto and "DNI" in texto


def test_el_consentimiento_informado_se_descarga_para_imprimir(client, entorno):
    r = client.get("/turnos/1/consentimiento-informado")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    texto = texto_del_pdf(r.content)
    assert "Consentimiento informado" in texto
    assert "Firma:" in texto
    assert "Se entrega en papel en el laboratorio de extracción" in texto
    assert "no se sube a la plataforma" in texto
    assert "menor de edad" in texto


def test_los_documentos_de_otro_paciente_dan_404(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="sofia.ramirez@example.com")
    assert client.get("/turnos/1/orden-extraccion").status_code == 404
    assert client.get("/turnos/1/consentimiento-informado").status_code == 404
    assert client.get("/turnos/99/orden-extraccion").status_code == 404


def test_un_turno_cancelado_ya_no_tiene_documentos(client, entorno):
    _, turnos, _ = entorno
    turnos.turnos[1].estado = CANCELADO
    r = client.get("/turnos/1/orden-extraccion")
    assert r.status_code == 409
    assert r.json()["code"] == "turno_no_vigente"
    assert client.get("/turnos/1/consentimiento-informado").status_code == 409
    (turno,) = client.get("/turnos/mis-turnos").json()
    assert turno["orden_extraccion_url"] is None


def test_solo_el_paciente_descarga_los_documentos(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert client.get("/turnos/1/orden-extraccion").status_code == 403
    assert client.get("/turnos/1/consentimiento-informado").status_code == 403
