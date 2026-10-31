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
from app.modules.turnos.reglas import ARG, LIMITE_INASISTENCIAS
from app.modules.turnos.repositorio import AUSENTE, RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fakes import AvisosCaido, AvisosEspia

LUCIA = "lucia.fernandez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)
DESPUES = INICIO + timedelta(minutes=30)  # the appointment time has passed


@pytest.fixture
def reloj():
    """The clock the services see: tests move it forward by assigning `reloj.ahora`."""

    class Reloj:
        ahora = AHORA

    app.dependency_overrides[reglas.ahora] = lambda: Reloj.ahora
    return Reloj


@pytest.fixture
def entorno(client, login_as, reloj):
    """Lucía's study is Pagado and has an appointment on Tuesday 3 November at 9:15."""
    estudios = RepositorioEstudiosEnMemoria()
    turnos = RepositorioTurnosEnMemoria()
    avisos = AvisosEspia()
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, AHORA)
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: turnos
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    login_as(Rol.PACIENTE, email=LUCIA)
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": INICIO.isoformat()},
    )
    assert r.status_code == 201
    avisos.enviados.clear()
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    return estudios, turnos, avisos


def siguiente_dia_habil(inicio: datetime) -> datetime:
    inicio += timedelta(days=1)
    while reglas.motivo_sin_turnos(inicio.date()):
        inicio += timedelta(days=1)
    return inicio


def reservar_otra_vez(client, login_as, inicio):
    login_as(Rol.PACIENTE, email=LUCIA)
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": inicio.isoformat()},
    )
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    return r


def test_registrar_la_inasistencia_avisa_la_cantidad_y_habilita_una_nueva_reserva(
    client, entorno, reloj
):
    estudios, turnos, avisos = entorno
    reloj.ahora = DESPUES
    r = client.post("/turnos/1/inasistencia")
    assert r.status_code == 200
    assert r.json()["inasistencias"] == 1
    assert r.json()["limite_alcanzado"] is False
    assert r.json()["turno"]["estado"] == "Ausente"
    assert r.json()["paciente_avisado"] is True
    # the study keeps its state: it is not blocked and not sent back to Pagado
    assert r.json()["estudio_estado"] == "TurnoSacado"
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert turnos.turnos[1].estado == AUSENTE
    assert turnos.turnos[1].recordatorio.anulado is True
    assert "Acumula 1 inasistencia." in avisos.para(LUCIA)[0]
    assert "reprogramar" in avisos.para(LUCIA)[0]


def test_no_se_registra_la_inasistencia_de_un_turno_futuro(client, entorno):
    r = client.post("/turnos/1/inasistencia")
    assert r.status_code == 409
    assert r.json()["code"] == "turno_futuro"
    assert entorno[1].turnos[1].estado == "Programado"


def test_no_se_registra_dos_veces_ni_sobre_un_turno_inexistente(client, entorno, reloj):
    reloj.ahora = DESPUES
    client.post("/turnos/1/inasistencia")
    r = client.post("/turnos/1/inasistencia")
    assert r.status_code == 409
    assert r.json()["code"] == "turno_no_vigente"
    assert client.post("/turnos/99/inasistencia").status_code == 404


def test_despues_de_la_inasistencia_el_paciente_puede_reprogramar(client, entorno, reloj, login_as):
    reloj.ahora = DESPUES
    client.post("/turnos/1/inasistencia")

    login_as(Rol.PACIENTE, email=LUCIA)
    assert client.get("/turnos/habilitados").json() == [
        {"estudio_id": 1, "estado": "TurnoSacado", "motivo": "nueva_reserva", "inasistencias": 1}
    ]
    nuevo = datetime(2026, 11, 4, 9, 0, tzinfo=ARG)
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": nuevo.isoformat()},
    )
    assert r.status_code == 201
    assert entorno[0].obtener(1).estado == EstadoEstudio.TURNO_SACADO  # "sigue en Turno sacado"
    estados = [t["estado"] for t in client.get("/turnos/mis-turnos").json()]
    assert sorted(estados) == ["Ausente", "Programado"]


def test_al_llegar_al_limite_avisa_pero_no_bloquea(client, entorno, reloj, login_as):
    estudios, turnos, avisos = entorno
    inicio = INICIO
    for numero in range(1, LIMITE_INASISTENCIAS + 1):
        reloj.ahora = inicio + timedelta(minutes=30)
        r = client.post(f"/turnos/{numero}/inasistencia")
        assert r.status_code == 200
        assert r.json()["inasistencias"] == numero
        assert r.json()["limite_alcanzado"] is (numero == LIMITE_INASISTENCIAS)
        # book again for the next round
        inicio = siguiente_dia_habil(inicio)
        reloj.ahora = inicio - timedelta(hours=3)
        nueva = reservar_otra_vez(client, login_as, inicio)
        assert nueva.status_code == 201, nueva.json()

    ultimo_aviso = [m for m in avisos.para(LUCIA) if "Acumula 5" in m][0]
    assert "límite de 5 inasistencias" in ultimo_aviso
    # no blocking: the sixth appointment was booked and the study is still enabled
    assert turnos.contar_inasistencias(1) == 5
    assert turnos.turno_vigente_de_estudio(1) is not None
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO


def test_la_agenda_del_laboratorio_muestra_los_turnos_programados(client, entorno, reloj):
    (turno,) = client.get("/turnos/agenda").json()
    assert turno["paciente"] == "Lucía Fernández"
    assert turno["ya_paso"] is False
    reloj.ahora = DESPUES
    assert client.get("/turnos/agenda").json()[0]["ya_paso"] is True
    client.post("/turnos/1/inasistencia")
    assert client.get("/turnos/agenda").json() == []


def test_cancelar_un_turno_que_ya_paso_se_rechaza_sin_registrar_nada(
    client, entorno, reloj, login_as
):
    reloj.ahora = DESPUES
    login_as(Rol.PACIENTE, email=LUCIA)
    r = client.post("/turnos/1/cancelar")
    assert r.status_code == 409
    assert "inasistencia" in r.json()["detalle"]
    assert entorno[1].contar_inasistencias(1) == 0


def test_si_el_aviso_falla_la_inasistencia_igual_queda_registrada(client, entorno, reloj):
    reloj.ahora = DESPUES
    app.dependency_overrides[obtener_avisos] = AvisosCaido
    r = client.post("/turnos/1/inasistencia")
    assert r.status_code == 200
    assert r.json()["paciente_avisado"] is False
    assert entorno[1].contar_inasistencias(1) == 1


def test_solo_el_administrativo_registra_inasistencias(client, entorno, reloj, login_as):
    reloj.ahora = DESPUES
    login_as(Rol.PACIENTE, email=LUCIA)
    assert client.post("/turnos/1/inasistencia").status_code == 403
    assert client.get("/turnos/agenda").status_code == 403
