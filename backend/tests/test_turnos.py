from datetime import date, datetime, timedelta

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations.avisos import obtener_avisos
from app.main import app
from app.modules.acceso.catalogs import PROVINCES
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from app.modules.turnos import reglas
from app.modules.turnos.reglas import ARG
from app.modules.turnos.repositorio import (
    Recordatorio,
    RepositorioTurnosEnMemoria,
)
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
SOFIA = "sofia.ramirez@example.com"
# Monday 2 November 2026, 10:07 in Argentina.
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
LUNES = date(2026, 11, 2)
MARTES = date(2026, 11, 3)


def a_las(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=ARG)


@pytest.fixture
def entorno(client, login_as):
    """Lucía's and Sofía's studies are Pagado; Martín's is still Creado."""
    estudios = RepositorioEstudiosEnMemoria()
    turnos = RepositorioTurnosEnMemoria()
    avisos = AvisosEspia()
    for estudio_id in (1, 3):
        estudios.cambiar_estado(estudio_id, EstadoEstudio.PAGADO, AHORA)
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: turnos
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[reglas.ahora] = lambda: AHORA
    login_as(Rol.PACIENTE, email=LUCIA)
    return estudios, turnos, avisos


def reservar(client, inicio, estudio=1, laboratorio=1):
    return client.post(
        "/turnos/reservas",
        json={"estudio_id": estudio, "laboratorio_id": laboratorio, "inicio": inicio.isoformat()},
    )


# --- the rule -----------------------------------------------------------------------------


def test_un_dia_habil_tiene_turnos_de_15_minutos_de_9_a_18():
    turnos = reglas.turnos_del_dia(LUNES)
    assert len(turnos) == 36
    assert turnos[0] == a_las(LUNES, 9, 0)
    assert turnos[1] == a_las(LUNES, 9, 15)
    assert turnos[-1] == a_las(LUNES, 17, 45)


@pytest.mark.parametrize(
    "dia", [date(2026, 11, 7), date(2026, 11, 8), date(2026, 11, 23), date(2026, 12, 25)]
)
def test_no_hay_turnos_los_fines_de_semana_ni_los_feriados(dia):
    assert reglas.turnos_del_dia(dia) == []
    assert reglas.motivo_sin_turnos(dia)


def test_solo_son_validos_los_horarios_de_la_regla():
    assert reglas.es_turno_valido(a_las(MARTES, 9, 15))
    assert not reglas.es_turno_valido(a_las(MARTES, 9, 10))
    assert not reglas.es_turno_valido(a_las(MARTES, 8, 45))
    assert not reglas.es_turno_valido(a_las(MARTES, 18, 0))
    assert not reglas.es_turno_valido(a_las(date(2026, 11, 7), 10, 0))


# --- the map of labs ---------------------------------------------------------------------


def test_hay_cien_laboratorios_repartidos_por_el_pais(client, entorno):
    r = client.get("/turnos/laboratorios")
    assert r.status_code == 200
    laboratorios = r.json()
    assert len(laboratorios) == 100
    assert len({lab["id"] for lab in laboratorios}) == 100
    assert {lab["provincia"] for lab in laboratorios} == set(PROVINCES)
    assert all(-56 < lab["latitud"] < -21 and -74 < lab["longitud"] < -53 for lab in laboratorios)


def test_se_filtran_los_laboratorios_por_provincia(client, entorno):
    r = client.get("/turnos/laboratorios", params={"provincia": "Córdoba"})
    assert {lab["provincia"] for lab in r.json()} == {"Córdoba"}


def test_cada_laboratorio_muestra_su_proximo_turno_libre(client, entorno):
    primero = client.get("/turnos/laboratorios").json()[0]
    assert primero["proximo_turno"] == a_las(LUNES, 10, 15).isoformat()


def test_el_proximo_turno_salta_el_fin_de_semana(client, entorno, monkeypatch):
    viernes_tarde = datetime(2026, 11, 6, 17, 50, tzinfo=ARG)
    app.dependency_overrides[reglas.ahora] = lambda: viernes_tarde
    primero = client.get("/turnos/laboratorios").json()[0]
    assert primero["proximo_turno"] == a_las(date(2026, 11, 9), 9, 0).isoformat()


# --- free appointments ------------------------------------------------------------------


def libres(client, dia, laboratorio=1):
    return client.get(
        f"/turnos/laboratorios/{laboratorio}/turnos-libres", params={"fecha": dia.isoformat()}
    )


def test_los_turnos_libres_de_hoy_no_incluyen_los_que_ya_pasaron(client, entorno):
    r = libres(client, LUNES)
    assert r.status_code == 200
    horarios = r.json()["turnos"]
    assert horarios[0] == a_las(LUNES, 10, 15).isoformat()
    assert len(horarios) == 31


def test_un_fin_de_semana_o_un_feriado_se_informa_sin_turnos(client, entorno):
    r = libres(client, date(2026, 11, 7))
    assert r.json()["turnos"] == []
    assert "lunes a viernes" in r.json()["motivo"]
    assert "feriado" in libres(client, date(2026, 11, 23)).json()["motivo"]


def test_no_se_ofrecen_fechas_pasadas_ni_demasiado_lejanas(client, entorno):
    assert libres(client, date(2026, 11, 1)).status_code == 422
    assert libres(client, LUNES + timedelta(days=61)).status_code == 422
    assert libres(client, LUNES + timedelta(days=60)).status_code == 200
    assert (
        client.get(
            "/turnos/laboratorios/999/turnos-libres", params={"fecha": "2026-11-03"}
        ).status_code
        == 404
    )


def test_si_el_laboratorio_no_tiene_turnos_libres_ese_dia_lo_informa(client, entorno):
    _, turnos, _ = entorno
    for inicio in reglas.turnos_del_dia(MARTES):
        turnos.crear_turno(99, 1, inicio, AHORA, Recordatorio(AHORA))
    r = libres(client, MARTES)
    assert r.json()["turnos"] == []
    assert "no tiene turnos libres" in r.json()["motivo"]
    # another lab still has them
    assert len(libres(client, MARTES, laboratorio=2).json()["turnos"]) == 36


# --- booking ------------------------------------------------------------------------------


def test_reservar_pasa_el_estudio_a_turno_sacado_y_programa_el_recordatorio(client, entorno):
    estudios, turnos, avisos = entorno
    inicio = a_las(date(2026, 11, 5), 9, 30)
    r = reservar(client, inicio)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "Programado"
    assert cuerpo["laboratorio"]["id"] == 1
    assert cuerpo["puede_cancelar"] is True
    assert datetime.fromisoformat(cuerpo["recordatorio_para"]) == inicio - timedelta(hours=24)

    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    (turno,) = turnos.turnos.values()
    assert (turno.estudio_id, turno.inicio) == (1, inicio)
    assert turno.recordatorio.canal == "email" and not turno.recordatorio.anulado
    assert "05/11/2026 a las 09:30" in avisos.para(LUCIA)[0]


def test_con_menos_de_un_dia_de_anticipo_el_recordatorio_sale_de_inmediato(client, entorno):
    r = reservar(client, a_las(LUNES, 11, 0))
    assert datetime.fromisoformat(r.json()["recordatorio_para"]) == AHORA


def test_un_estudio_autorizado_tambien_puede_sacar_turno(client, entorno, login_as):
    estudios, _, _ = entorno
    estudios.cambiar_estado(2, EstadoEstudio.AUTORIZADO, AHORA)
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    assert reservar(client, a_las(MARTES, 9), estudio=2).status_code == 201


def test_un_estudio_creado_no_puede_sacar_turno(client, entorno, login_as):
    login_as(Rol.PACIENTE, email="martin.gomez@example.com")
    r = reservar(client, a_las(MARTES, 9), estudio=2)
    assert r.status_code == 409
    assert r.json()["code"] == "estudio_no_habilitado"
    assert entorno[1].turnos == {}


def test_un_estudio_no_puede_tener_dos_turnos(client, entorno):
    reservar(client, a_las(MARTES, 9))
    r = reservar(client, a_las(MARTES, 10))
    assert r.status_code == 409
    assert r.json()["code"] == "ya_tiene_turno"


def test_un_turno_es_para_una_sola_persona_y_se_informan_los_libres_actualizados(
    client, entorno, login_as
):
    inicio = a_las(MARTES, 9)
    assert reservar(client, inicio).status_code == 201
    login_as(Rol.PACIENTE, email=SOFIA)
    r = reservar(client, inicio, estudio=3)
    assert r.status_code == 409
    assert r.json()["code"] == "turno_ocupado"
    assert entorno[0].obtener(3).estado == EstadoEstudio.PAGADO  # still able to book another
    actualizados = libres(client, MARTES).json()["turnos"]
    assert inicio.isoformat() not in actualizados
    assert len(actualizados) == 35
    assert reservar(client, a_las(MARTES, 9, 15), estudio=3).status_code == 201


def test_cada_laboratorio_tiene_su_propio_turnero(client, entorno, login_as):
    inicio = a_las(MARTES, 9)
    assert reservar(client, inicio, laboratorio=1).status_code == 201
    login_as(Rol.PACIENTE, email=SOFIA)
    assert reservar(client, inicio, estudio=3, laboratorio=2).status_code == 201


@pytest.mark.parametrize(
    "inicio",
    [
        a_las(MARTES, 9, 10),
        a_las(MARTES, 18, 0),
        a_las(date(2026, 11, 7), 10, 0),
        a_las(date(2026, 11, 23), 10, 0),
        a_las(LUNES, 9, 0),
        a_las(LUNES + timedelta(days=61), 9, 0),
    ],
)
def test_un_horario_fuera_de_la_regla_o_del_pasado_se_rechaza(client, entorno, inicio):
    r = reservar(client, inicio)
    assert r.status_code == 422
    assert r.json()["code"] == "turno_invalido"
    assert entorno[0].obtener(1).estado == EstadoEstudio.PAGADO


def test_un_horario_sin_zona_horaria_se_lee_en_hora_argentina(client, entorno):
    r = client.post(
        "/turnos/reservas",
        json={"estudio_id": 1, "laboratorio_id": 1, "inicio": "2026-11-03T09:00:00"},
    )
    assert r.status_code == 201
    assert datetime.fromisoformat(r.json()["inicio"]) == a_las(MARTES, 9)


def test_no_se_reserva_el_estudio_de_otro_ni_en_un_laboratorio_inexistente(client, entorno):
    assert reservar(client, a_las(MARTES, 9), estudio=3).status_code == 404
    assert reservar(client, a_las(MARTES, 9), laboratorio=999).status_code == 404


def test_se_listan_los_estudios_habilitados_y_los_turnos_del_paciente(client, entorno):
    assert client.get("/turnos/habilitados").json() == [
        {
            "estudio_id": 1,
            "estado": "Pagado",
            "motivo": "pagado",
            "inasistencias": 0,
            "remuestreo_motivo": None,
        }
    ]
    reservar(client, a_las(MARTES, 9))
    assert client.get("/turnos/habilitados").json() == []
    (turno,) = client.get("/turnos/mis-turnos").json()
    assert turno["estudio_id"] == 1 and turno["estado"] == "Programado"


def test_los_endpoints_de_turnos_exigen_el_rol_paciente(client, entorno, login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    assert client.get("/turnos/laboratorios").status_code == 403
    assert reservar(client, a_las(MARTES, 9)).status_code == 403
    assert client.get("/turnos/mis-turnos").status_code == 403
