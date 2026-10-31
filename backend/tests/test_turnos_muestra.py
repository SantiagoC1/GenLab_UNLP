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
from app.modules.turnos.repositorio import REALIZADO, RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)
DESPUES = datetime(2026, 11, 3, 9, 40, tzinfo=ARG)


@pytest.fixture
def entorno(client, login_as):
    """Lucía's study has an appointment; the clock is at the end of it."""
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
    app.dependency_overrides[reglas.ahora] = lambda: DESPUES
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    return estudios, turnos


def notificar(client, volumen, estudio=1):
    return client.post(
        "/turnos/notificaciones-muestra", json={"estudio_id": estudio, "volumen_ml": volumen}
    )


@pytest.mark.parametrize("volumen", [2, 2.0, 2.5, 10])
def test_con_al_menos_2_ml_el_estudio_pasa_a_listo_para_retirar(client, entorno, volumen):
    estudios, turnos = entorno
    r = notificar(client, volumen)
    assert r.status_code == 200
    assert r.json()["estado"] == "ListoParaRetirar"
    assert r.json()["volumen_suficiente"] is True
    assert r.json()["listo_para_retirar"] is True
    assert estudios.obtener(1).estado == EstadoEstudio.LISTO_PARA_RETIRAR
    # the appointment was attended and the sample is registered in the study
    assert turnos.turnos[1].estado == REALIZADO
    (muestra,) = turnos.listar_muestras(1)
    assert (muestra.volumen_ml, muestra.tomada_en) == (volumen, DESPUES)


@pytest.mark.parametrize("volumen", [0.5, 1.99])
def test_con_menos_de_2_ml_no_se_habilita_el_retiro(client, entorno, volumen):
    estudios, turnos = entorno
    r = notificar(client, volumen)
    assert r.status_code == 200
    assert r.json()["volumen_suficiente"] is False
    assert r.json()["listo_para_retirar"] is False
    assert r.json()["estado"] == "TurnoSacado"
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    # the insufficient sample is kept in the history
    assert [m.volumen_ml for m in turnos.listar_muestras(1)] == [volumen]


@pytest.mark.parametrize("volumen", [0, -1, 51, "mucho"])
def test_el_volumen_tiene_que_ser_un_numero_positivo_razonable(client, entorno, volumen):
    assert notificar(client, volumen).status_code == 422
    assert entorno[1].muestras == []


def test_no_se_notifica_dos_veces_la_misma_muestra(client, entorno):
    notificar(client, 3)
    r = notificar(client, 3)
    assert r.status_code == 409
    assert r.json()["code"] == "sin_turno_vigente"
    assert len(entorno[1].muestras) == 1


def test_un_estudio_sin_turno_o_inexistente_se_rechaza(client, entorno):
    assert notificar(client, 3, estudio=2).status_code == 409
    assert notificar(client, 3, estudio=99).status_code == 404


def test_la_notificacion_sin_intervencion_de_personas_no_necesita_otra_accion(client, entorno):
    # one call is enough: the study is ready to be picked up without any other step
    notificar(client, 4)
    assert entorno[0].obtener(1).estado == EstadoEstudio.LISTO_PARA_RETIRAR
    assert [(c.desde, c.hacia) for c in entorno[0].obtener(1).historial][-1] == (
        EstadoEstudio.TURNO_SACADO,
        EstadoEstudio.LISTO_PARA_RETIRAR,
    )


def test_la_agenda_ya_no_muestra_el_turno_cuya_muestra_se_notifico(client, entorno):
    assert len(client.get("/turnos/agenda").json()) == 1
    notificar(client, 3)
    assert client.get("/turnos/agenda").json() == []


def test_el_endpoint_exige_la_sesion_del_administrativo(client, entorno, login_as):
    login_as(Rol.PACIENTE, email=LUCIA)
    assert notificar(client, 3).status_code == 403
    login_as(Rol.TRANSPORTISTA)
    assert notificar(client, 3).status_code == 403
