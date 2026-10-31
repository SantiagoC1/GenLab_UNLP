from datetime import UTC, datetime

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations.avisos import obtener_avisos
from app.integrations.obras_sociales import obtener_obras_sociales
from app.main import app
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from tests.fakes import AvisosCaido, AvisosEspia, ObrasSocialesFalsa

LUCIA = "lucia.fernandez@example.com"


@pytest.fixture
def entorno(client, login_as):
    """Lucía chose OSDE (pending); Martín has a budget but no coverage."""
    repositorio = RepositorioEstudiosEnMemoria()
    avisos = AvisosEspia()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[obtener_obras_sociales] = ObrasSocialesFalsa
    for estudio_id, importe in ((1, 500), (2, 590)):
        repositorio.guardar_presupuesto(estudio_id, importe, datetime.now(UTC))
    login_as(Rol.PACIENTE, email=LUCIA)
    client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    return repositorio, avisos


def responder(client, resultado, motivo=None, estudio=1):
    cuerpo = {"resultado": resultado} | ({"motivo": motivo} if motivo else {})
    return client.post(f"/presupuesto_pago/estudios/{estudio}/autorizacion", json=cuerpo)


def test_la_bandeja_lista_los_estudios_con_la_autorizacion_pendiente(client, entorno):
    r = client.get("/presupuesto_pago/autorizaciones-pendientes")
    assert r.status_code == 200
    assert r.json() == [
        {
            "estudio_id": 1,
            "paciente": "Lucía Fernández",
            "obra_social": "OSDE",
            "porcentaje": 80,
            "importe_usd": 500,
            "estado_estudio": "Creado",
        }
    ]


def test_autorizar_pasa_el_estudio_a_autorizado_asienta_la_operacion_y_avisa(client, entorno):
    repositorio, avisos = entorno
    r = responder(client, "Autorizado")
    assert r.status_code == 200
    assert r.json()["estado"] == "Autorizado"
    assert r.json()["paciente_avisado"] is True
    estudio = repositorio.obtener(1)
    assert estudio.estado == EstadoEstudio.AUTORIZADO
    assert estudio.cobertura.estado == "Autorizado"
    assert estudio.cobertura.resuelta_en is not None

    (asiento,) = repositorio.asientos
    assert (asiento.estudio_id, asiento.importe_usd) == (1, 500)
    assert "OSDE" in asiento.metodo
    assert "turno" in avisos.para(LUCIA)[0]
    assert client.get("/presupuesto_pago/autorizaciones-pendientes").json() == []


def test_rechazar_guarda_el_motivo_pasa_a_rechazado_y_avisa(client, entorno):
    repositorio, avisos = entorno
    r = responder(client, "Rechazado", "El estudio no está en el nomenclador.")
    assert r.status_code == 200
    assert r.json()["estado"] == "Rechazado"
    assert r.json()["motivo"] == "El estudio no está en el nomenclador."
    estudio = repositorio.obtener(1)
    assert estudio.estado == EstadoEstudio.RECHAZADO
    assert estudio.cobertura.motivo_rechazo == "El estudio no está en el nomenclador."
    assert "nomenclador" in avisos.para(LUCIA)[0]
    assert repositorio.asientos == []


def test_el_rechazo_exige_el_motivo(client, entorno):
    assert responder(client, "Rechazado").status_code == 422
    assert responder(client, "Rechazado", "   ").status_code == 422
    assert entorno[0].obtener(1).estado == EstadoEstudio.CREADO


def test_la_respuesta_tiene_que_ser_autorizado_o_rechazado(client, entorno):
    assert responder(client, "Pendiente").status_code == 422


def test_el_estudio_no_avanza_hasta_que_se_registra_la_respuesta(client, entorno):
    repositorio, _ = entorno
    assert repositorio.obtener(1).estado == EstadoEstudio.CREADO
    assert repositorio.obtener(1).cobertura.estado == "Pendiente"


def test_no_se_responde_dos_veces_ni_sin_cobertura(client, entorno):
    responder(client, "Autorizado")
    assert responder(client, "Autorizado").status_code == 409
    assert responder(client, "Rechazado", "otro").status_code == 409
    sin_cobertura = responder(client, "Autorizado", estudio=2)
    assert sin_cobertura.status_code == 409
    assert sin_cobertura.json()["code"] == "sin_autorizacion_pendiente"
    assert responder(client, "Autorizado", estudio=99).status_code == 404


def test_un_estudio_autorizado_ya_no_admite_el_pago_particular(client, entorno, login_as):
    responder(client, "Autorizado")
    login_as(Rol.PACIENTE, email=LUCIA)
    r = client.post("/presupuesto_pago/mis-estudios/1/pago", json={"metodo": "transferencia"})
    assert r.status_code == 409
    assert "Autorizado" in r.json()["detalle"]


def test_el_paciente_ve_el_motivo_del_rechazo(client, entorno, login_as):
    responder(client, "Rechazado", "Sin cobertura para estudios genéticos.")
    login_as(Rol.PACIENTE, email=LUCIA)
    cobertura = client.get("/presupuesto_pago/mis-estudios").json()[0]["cobertura"]
    assert cobertura["estado"] == "Rechazado"
    assert cobertura["motivo_rechazo"] == "Sin cobertura para estudios genéticos."


def test_si_el_aviso_falla_la_respuesta_igual_queda_registrada(client, entorno):
    app.dependency_overrides[obtener_avisos] = AvisosCaido
    r = responder(client, "Autorizado")
    assert r.status_code == 200
    assert r.json()["paciente_avisado"] is False
    assert entorno[0].obtener(1).estado == EstadoEstudio.AUTORIZADO


def test_solo_el_administrativo_registra_la_respuesta(client, entorno, login_as):
    login_as(Rol.PACIENTE, email=LUCIA)
    assert responder(client, "Autorizado").status_code == 403
    assert client.get("/presupuesto_pago/autorizaciones-pendientes").status_code == 403
    assert entorno[0].obtener(1).estado == EstadoEstudio.CREADO
