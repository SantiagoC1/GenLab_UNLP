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
from app.modules.turnos.reglas import ARG, MOTIVO_ADN, MOTIVO_VOLUMEN
from app.modules.turnos.repositorio import RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
DOCTORA = "ana.perez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)
OTRO_INICIO = datetime(2026, 11, 4, 9, 15, tzinfo=ARG)

HACIA_EL_ANALISIS = (
    EstadoEstudio.LISTO_PARA_RETIRAR,
    EstadoEstudio.EN_CAMINO_AL_LABORATORIO_CENTRAL,
    EstadoEstudio.EN_LABORATORIO_CENTRAL,
    EstadoEstudio.EN_VIAJE_A_COREA,
    EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA,
    EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO,
)


@pytest.fixture
def entorno(client, login_as):
    """Lucía's study (requested by Ana Pérez) is Pagado and has an appointment."""
    estudios = RepositorioEstudiosEnMemoria()
    turnos = RepositorioTurnosEnMemoria()
    avisos = AvisosEspia()
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, AHORA)
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: turnos
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[reglas.ahora] = lambda: AHORA
    login_as(Rol.PACIENTE, email=LUCIA)
    reservar(client, INICIO)
    avisos.enviados.clear()
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    return estudios, turnos, avisos


def reservar(client, inicio):
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": inicio.isoformat()},
    )
    assert r.status_code == 201, r.json()
    return r.json()


def notificar(client, volumen):
    return client.post(
        "/turnos/notificaciones-muestra", json={"estudio_id": 1, "volumen_ml": volumen}
    )


# --- less than 2 ml ---------------------------------------------------------------------------


def test_con_menos_de_2_ml_se_habilita_un_remuestreo_y_se_avisa_al_medico_y_al_paciente(
    client, entorno
):
    estudios, turnos, avisos = entorno
    r = notificar(client, 1.5)
    assert r.status_code == 200
    remuestreo = r.json()["remuestreo"]
    assert remuestreo["motivo"] == MOTIVO_VOLUMEN
    assert remuestreo["detalle"] == "Muestra de 1.5 ml"
    assert remuestreo["medico_avisado"] is True
    assert remuestreo["paciente_avisado"] is True
    assert r.json()["listo_para_retirar"] is False

    assert "nueva muestra" in avisos.para(DOCTORA)[0]
    assert "Lucía Fernández" in avisos.para(DOCTORA)[0]
    assert "sin costo" in avisos.para(LUCIA)[0].replace("no tiene costo", "sin costo")
    # same study, still TurnoSacado, previous sample kept, nothing charged
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert len(estudios.estudios) == 3
    assert estudios.asientos == []
    assert [m.volumen_ml for m in turnos.listar_muestras(1)] == [1.5]


def test_una_muestra_suficiente_no_genera_remuestreo(client, entorno):
    r = notificar(client, 3)
    assert r.json()["remuestreo"] is None
    assert entorno[1].remuestreos == []
    assert entorno[2].enviados == []


def test_el_paciente_queda_habilitado_para_un_nuevo_turno_hasta_que_lo_reserva(
    client, entorno, login_as
):
    notificar(client, 1)
    login_as(Rol.PACIENTE, email=LUCIA)
    pendientes = client.get("/turnos/habilitados").json()
    assert pendientes == [
        {
            "estudio_id": 1,
            "estado": "TurnoSacado",
            "motivo": "nueva_reserva",
            "inasistencias": 0,
            "remuestreo_motivo": MOTIVO_VOLUMEN,
        }
    ]
    # if the patient does not book, the study stays stopped and the notice stays pending
    assert client.get("/turnos/habilitados").json() == pendientes

    reservar(client, OTRO_INICIO)
    assert client.get("/turnos/habilitados").json() == []
    assert entorno[0].obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert entorno[1].remuestreo_pendiente(1) is None
    assert entorno[0].asientos == []  # no new charge


def test_cancelar_el_turno_de_un_remuestreo_no_devuelve_el_estudio_a_pagado(
    client, entorno, login_as
):
    notificar(client, 1)
    login_as(Rol.PACIENTE, email=LUCIA)
    nuevo = reservar(client, OTRO_INICIO)
    r = client.post(f"/turnos/{nuevo['id']}/cancelar")
    assert r.status_code == 200
    assert r.json()["estudio_estado"] == "TurnoSacado"
    assert client.get("/turnos/habilitados").json()[0]["motivo"] == "nueva_reserva"


def test_se_puede_repetir_el_ciclo_si_la_segunda_muestra_tambien_es_insuficiente(
    client, entorno, login_as
):
    notificar(client, 1)
    login_as(Rol.PACIENTE, email=LUCIA)
    reservar(client, OTRO_INICIO)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    r = notificar(client, 1.9)
    assert r.json()["remuestreo"]["motivo"] == MOTIVO_VOLUMEN
    assert [m.volumen_ml for m in entorno[1].listar_muestras(1)] == [1, 1.9]
    assert len(entorno[1].remuestreos) == 2


# --- DNA not enough, reported by the bioinformatician ------------------------------------------


@pytest.fixture
def en_analisis(client, entorno, login_as):
    estudios, turnos, avisos = entorno
    # the lab reported a good sample, so the appointment was attended
    notificar(client, 3)
    estudios.cambiar_estado(1, EstadoEstudio.EN_CAMINO_AL_LABORATORIO_CENTRAL, AHORA)
    for estado in HACIA_EL_ANALISIS[2:]:
        estudios.cambiar_estado(1, estado, AHORA)
    avisos.enviados.clear()
    login_as(Rol.BIOINFORMATICO)
    return estudios, turnos, avisos


def test_con_adn_insuficiente_el_bioinformatico_habilita_el_remuestreo(client, en_analisis):
    estudios, turnos, avisos = en_analisis
    r = client.post("/turnos/estudios/1/remuestreo", json={"detalle": "ADN desnaturalizado"})
    assert r.status_code == 200
    assert r.json()["motivo"] == MOTIVO_ADN
    assert r.json()["estado"] == "TurnoSacado"
    assert r.json()["medico_avisado"] and r.json()["paciente_avisado"]
    assert "ADN" in avisos.para(DOCTORA)[0]
    assert "ADN" in avisos.para(LUCIA)[0]
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert estudios.asientos == []


def test_despues_del_adn_insuficiente_el_paciente_reserva_un_nuevo_turno(
    client, en_analisis, login_as
):
    client.post("/turnos/estudios/1/remuestreo", json={})
    login_as(Rol.PACIENTE, email=LUCIA)
    habilitado = client.get("/turnos/habilitados").json()[0]
    assert habilitado["remuestreo_motivo"] == MOTIVO_ADN
    reservar(client, OTRO_INICIO)
    assert client.get("/turnos/habilitados").json() == []
    assert en_analisis[0].obtener(1).estado == EstadoEstudio.TURNO_SACADO


def test_el_adn_insuficiente_solo_se_informa_durante_el_analisis(client, entorno, login_as):
    login_as(Rol.BIOINFORMATICO)
    r = client.post("/turnos/estudios/1/remuestreo", json={})
    assert r.status_code == 409
    assert r.json()["code"] == "estudio_no_en_analisis"
    assert client.post("/turnos/estudios/99/remuestreo", json={}).status_code == 404


def test_solo_el_bioinformatico_informa_el_adn_insuficiente(client, en_analisis, login_as):
    for rol in (Rol.PACIENTE, Rol.ADMINISTRATIVO_LABORATORIO, Rol.MEDICO_TRATANTE):
        login_as(rol, email=LUCIA)
        assert client.post("/turnos/estudios/1/remuestreo", json={}).status_code == 403
    assert en_analisis[0].obtener(1).estado == EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO
