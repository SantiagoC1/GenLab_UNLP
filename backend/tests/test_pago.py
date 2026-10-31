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
def entorno(login_as):
    repositorio = RepositorioEstudiosEnMemoria()
    avisos = AvisosEspia()
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[obtener_obras_sociales] = ObrasSocialesFalsa
    repositorio.guardar_presupuesto(1, 500, datetime.now(UTC))
    repositorio.guardar_presupuesto(2, 590, datetime.now(UTC))
    login_as(Rol.PACIENTE, email=LUCIA)
    return repositorio, avisos


def pagar(client, estudio_id=1, metodo="tarjeta_credito"):
    return client.post(f"/presupuesto_pago/mis-estudios/{estudio_id}/pago", json={"metodo": metodo})


def test_pagar_asienta_el_pago_pasa_el_estudio_a_pagado_y_avisa(client, entorno):
    repositorio, avisos = entorno
    r = pagar(client)
    assert r.status_code == 201
    assert r.json()["estado"] == "Pagado"
    assert r.json()["importe_usd"] == 500
    assert r.json()["paciente_avisado"] is True
    assert repositorio.obtener(1).estado == EstadoEstudio.PAGADO
    assert "turno" in avisos.para(LUCIA)[0]

    (asiento,) = repositorio.asientos
    assert (asiento.estudio_id, asiento.paciente, asiento.importe_usd) == (
        1,
        "Lucía Fernández",
        500,
    )
    assert asiento.metodo == "tarjeta_credito"
    assert asiento.fecha is not None
    assert asiento.cupon is None


def test_el_registro_financiero_lo_ve_el_administrativo(client, entorno, login_as):
    pagar(client)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    r = client.get("/presupuesto_pago/registro-financiero")
    assert r.status_code == 200
    assert r.json()[0]["paciente"] == "Lucía Fernández"
    assert r.json()[0]["metodo"] == "tarjeta_credito"
    login_as(Rol.PACIENTE, email=LUCIA)
    assert client.get("/presupuesto_pago/registro-financiero").status_code == 403


def test_si_el_paciente_no_paga_no_se_registra_nada(client, entorno):
    repositorio, _ = entorno
    client.get("/presupuesto_pago/mis-estudios")
    assert repositorio.obtener(1).estado == EstadoEstudio.CREADO
    assert repositorio.asientos == []


def test_no_se_paga_dos_veces(client, entorno):
    repositorio, _ = entorno
    pagar(client)
    r = pagar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "estudio_ya_pago"
    assert len(repositorio.asientos) == 1


def test_un_estudio_autorizado_se_considera_autorizado_y_pagado(client, entorno):
    repositorio, _ = entorno
    repositorio.cambiar_estado(1, EstadoEstudio.AUTORIZADO, datetime.now(UTC))
    r = pagar(client)
    assert r.status_code == 409
    assert "Autorizado" in r.json()["detalle"]
    assert repositorio.asientos == []


def test_no_se_paga_sin_presupuesto(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="sofia.ramirez@example.com")
    assert pagar(client, 3).status_code == 409


def test_no_se_paga_con_una_cobertura_en_curso(client, entorno):
    repositorio, _ = entorno
    client.post("/presupuesto_pago/mis-estudios/1/cobertura", json={"obra_social": "OSDE"})
    r = pagar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "cobertura_en_curso"
    assert repositorio.obtener(1).estado == EstadoEstudio.CREADO


def test_el_metodo_de_pago_tiene_que_ser_uno_de_los_ofrecidos(client, entorno):
    assert pagar(client, metodo="bitcoin").status_code == 422


def test_un_paciente_no_paga_el_estudio_de_otro(client, entorno):
    assert pagar(client, 2).status_code == 404


def test_si_el_aviso_falla_el_pago_igual_queda_asentado(client, entorno):
    repositorio, _ = entorno
    app.dependency_overrides[obtener_avisos] = AvisosCaido
    r = pagar(client)
    assert r.status_code == 201
    assert r.json()["paciente_avisado"] is False
    assert len(repositorio.asientos) == 1


def test_solo_el_paciente_paga(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert pagar(client).status_code == 403
