from datetime import datetime, timedelta

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
MARTIN = "martin.gomez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)


@pytest.fixture
def entorno(client, login_as):
    """Lucía's study is Pagado and Martín's is Autorizado; each has an appointment."""
    estudios = RepositorioEstudiosEnMemoria()
    turnos = RepositorioTurnosEnMemoria()
    avisos = AvisosEspia()
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, AHORA)
    estudios.cambiar_estado(2, EstadoEstudio.AUTORIZADO, AHORA)
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: turnos
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[reglas.ahora] = lambda: AHORA
    for contacto, estudio_id, inicio in (
        (LUCIA, 1, INICIO),
        (MARTIN, 2, INICIO + timedelta(hours=1)),
    ):
        login_as(Rol.PACIENTE, email=contacto)
        r = client.post(
            "/turnos/reservas",
            json={"estudio_id": estudio_id, "laboratorio_id": 1, "inicio": inicio.isoformat()},
        )
        assert r.status_code == 201
    login_as(Rol.PACIENTE, email=LUCIA)
    return estudios, turnos, avisos


def test_cancelar_libera_el_turno_anula_el_recordatorio_y_devuelve_el_estudio_a_pagado(
    client, entorno
):
    estudios, turnos, avisos = entorno
    r = client.post("/turnos/1/cancelar")
    assert r.status_code == 200
    assert r.json()["turno"]["estado"] == "Cancelado"
    assert r.json()["turno"]["recordatorio_para"] is None
    assert r.json()["turno"]["orden_extraccion_url"] is None
    assert r.json()["estudio_estado"] == "Pagado"

    assert estudios.obtener(1).estado == EstadoEstudio.PAGADO
    assert turnos.turnos[1].estado == CANCELADO
    assert turnos.turnos[1].recordatorio.anulado is True
    assert "Canceló su turno" in avisos.para(LUCIA)[-1]


def test_un_estudio_autorizado_vuelve_a_autorizado(client, entorno, login_as):
    estudios, _, _ = entorno
    login_as(Rol.PACIENTE, email=MARTIN)
    r = client.post("/turnos/2/cancelar")
    assert r.status_code == 200
    assert r.json()["estudio_estado"] == "Autorizado"
    assert estudios.obtener(2).estado == EstadoEstudio.AUTORIZADO


def test_el_turno_cancelado_queda_libre_para_otra_persona_y_se_puede_sacar_uno_nuevo(
    client, entorno, login_as
):
    client.post("/turnos/1/cancelar")
    libres = client.get(
        "/turnos/laboratorios/1/turnos-libres", params={"fecha": "2026-11-03"}
    ).json()["turnos"]
    assert INICIO.isoformat() in libres

    assert client.get("/turnos/habilitados").json() == [
        {
            "estudio_id": 1,
            "estado": "Pagado",
            "motivo": "pagado",
            "inasistencias": 0,
            "remuestreo_motivo": None,
        }
    ]
    otra_vez = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": INICIO.isoformat()},
    )
    assert otra_vez.status_code == 201


def test_un_turno_cuya_hora_ya_paso_no_se_cancela(client, entorno):
    estudios, turnos, _ = entorno
    app.dependency_overrides[reglas.ahora] = lambda: INICIO + timedelta(minutes=5)
    r = client.post("/turnos/1/cancelar")
    assert r.status_code == 409
    assert r.json()["code"] == "turno_pasado"
    assert turnos.turnos[1].estado == "Programado"
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO


def test_no_se_cancela_dos_veces(client, entorno):
    client.post("/turnos/1/cancelar")
    r = client.post("/turnos/1/cancelar")
    assert r.status_code == 409
    assert r.json()["code"] == "turno_no_vigente"


def test_no_se_cancela_el_turno_de_otro_paciente(client, entorno):
    assert client.post("/turnos/2/cancelar").status_code == 404
    assert client.post("/turnos/99/cancelar").status_code == 404
    assert entorno[1].turnos[2].estado == "Programado"


def test_si_el_estudio_viene_de_un_remuestreo_cancelar_solo_habilita_una_nueva_reserva(
    client, entorno, login_as
):
    estudios, turnos, _ = entorno
    # Study 3 was analysed, its DNA was not enough and it went back to TurnoSacado.
    for estado in (
        EstadoEstudio.PAGADO,
        EstadoEstudio.TURNO_SACADO,
        EstadoEstudio.LISTO_PARA_RETIRAR,
        EstadoEstudio.EN_CAMINO_AL_LABORATORIO_CENTRAL,
        EstadoEstudio.EN_LABORATORIO_CENTRAL,
        EstadoEstudio.EN_VIAJE_A_COREA,
        EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA,
        EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO,
        EstadoEstudio.TURNO_SACADO,
    ):
        estudios.cambiar_estado(3, estado, AHORA)
    login_as(Rol.PACIENTE, email="sofia.ramirez@example.com")
    r = client.post(
        "/turnos/reservas",
        json={
            "estudio_id": 3,
            "laboratorio_id": 1,
            "inicio": (INICIO + timedelta(hours=2)).isoformat(),
        },
    )
    assert r.status_code == 201

    cancelado = client.post(f"/turnos/{r.json()['id']}/cancelar")
    assert cancelado.status_code == 200
    # it never was Pagado again: it stays in TurnoSacado, with a new booking enabled
    assert cancelado.json()["estudio_estado"] == "TurnoSacado"
    assert estudios.obtener(3).estado == EstadoEstudio.TURNO_SACADO
    assert client.get("/turnos/habilitados").json() == [
        {
            "estudio_id": 3,
            "estado": "TurnoSacado",
            "motivo": "nueva_reserva",
            "inasistencias": 0,
            "remuestreo_motivo": None,
        }
    ]


def test_solo_el_paciente_cancela(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert client.post("/turnos/1/cancelar").status_code == 403
