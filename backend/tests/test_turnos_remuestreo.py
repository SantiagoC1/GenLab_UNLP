from datetime import datetime
from typing import get_args

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations.avisos import obtener_avisos
from app.main import app
from app.modules.presupuesto_pago.estado import can_transition
from app.modules.presupuesto_pago.repositorio import obtener_repositorio
from app.modules.presupuesto_pago.repositorio_memoria import RepositorioEstudiosEnMemoria
from app.modules.turnos import reglas
from app.modules.turnos.reglas import ARG, MOTIVO_ADN, MOTIVO_CALIDAD, MOTIVOS_REMUESTREO
from app.modules.turnos.repositorio import RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from app.modules.turnos.schemas import RemuestreoAdministrativoEntrada
from app.modules.turnos.servicio import (
    CAUSAS_DE_REMUESTREO,
    ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO,
)
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
DOCTORA = "ana.perez@example.com"
AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
INICIO = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)
OTRO_INICIO = datetime(2026, 11, 4, 9, 15, tzinfo=ARG)

HACIA_COREA = (
    EstadoEstudio.LISTO_PARA_RETIRAR,
    EstadoEstudio.EN_CAMINO_AL_LABORATORIO_CENTRAL,
    EstadoEstudio.EN_LABORATORIO_CENTRAL,
    EstadoEstudio.EN_VIAJE_A_COREA,
)
HACIA_BIOINFORMATICA = (*HACIA_COREA, EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA)
HACIA_EL_ANALISIS = (*HACIA_BIOINFORMATICA, EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO)
MOTIVO = "La muestra llegó hemolizada."


@pytest.fixture
def entorno(client, login_as, remuestreos):
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


def pedir(client, detalle=MOTIVO, estudio=1, motivo=MOTIVO_CALIDAD):
    return client.post(
        f"/turnos/estudios/{estudio}/remuestreo-administrativo",
        json={"motivo": motivo, "detalle": detalle},
    )


def remuestreables(client):
    r = client.get("/turnos/estudios/remuestreables")
    assert r.status_code == 200, r.text
    return r.json()


def llevar_a(estudios, estados, estudio=1):
    for estado in estados:
        estudios.cambiar_estado(estudio, estado, AHORA)


@pytest.fixture
def en_corea(client, entorno):
    """The sample was received and the study travels to Korea."""
    estudios, turnos, avisos = entorno
    assert notificar(client, 3).status_code == 200
    llevar_a(estudios, HACIA_COREA[1:])
    avisos.enviados.clear()
    return entorno


# --- a small volume no longer opens a resampling ----------------------------------------------


def test_un_volumen_chico_no_genera_remuestreo(client, entorno, remuestreos):
    r = notificar(client, 0.5)
    assert r.json()["listo_para_retirar"] is True
    assert remuestreos.listar(1) == []
    assert entorno[2].enviados == []


# --- the administrative user asks for it -------------------------------------------------------


@pytest.mark.parametrize("desde", [HACIA_COREA, HACIA_BIOINFORMATICA])
def test_el_administrativo_pide_el_remuestreo_desde_corea_o_la_bioinformatica(
    client, entorno, remuestreos, desde
):
    estudios, turnos, avisos = entorno
    notificar(client, 3)
    llevar_a(estudios, desde[1:])
    avisos.enviados.clear()

    r = pedir(client)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["motivo"] == MOTIVO_CALIDAD
    assert cuerpo["detalle"] == MOTIVO
    assert cuerpo["estado"] == "TurnoSacado"
    assert cuerpo["medico_avisado"] is True and cuerpo["paciente_avisado"] is True
    assert "nueva muestra" in avisos.para(DOCTORA)[0]
    assert "mala calidad" in avisos.para(DOCTORA)[0]
    assert "no tiene costo" in avisos.para(LUCIA)[0]
    # same study, no new study, nothing charged, previous sample kept
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert len(estudios.estudios) == 3
    assert estudios.asientos == []
    assert [m.volumen_ml for m in turnos.listar_muestras(1)] == [3]
    (guardado,) = remuestreos.listar(1)
    assert (guardado.motivo, guardado.detalle, guardado.pedido_por) == (
        MOTIVO_CALIDAD,
        MOTIVO,
        "u-sesion",
    )
    assert guardado.resuelto is False


def test_el_remuestreo_del_administrativo_queda_en_el_historial_del_estudio(client, en_corea):
    pedir(client)
    historial = [(c.desde, c.hacia) for c in en_corea[0].obtener(1).historial]
    assert historial[-1] == (EstadoEstudio.EN_VIAJE_A_COREA, EstadoEstudio.TURNO_SACADO)


@pytest.mark.parametrize("detalle", ["", "   ", "ab"])
def test_el_detalle_es_obligatorio(client, en_corea, remuestreos, detalle):
    r = pedir(client, detalle)
    assert r.status_code == 422
    assert remuestreos.listar(1) == []
    assert en_corea[0].obtener(1).estado == EstadoEstudio.EN_VIAJE_A_COREA


def test_el_detalle_se_guarda_sin_espacios_de_mas(client, en_corea, remuestreos):
    pedir(client, "  Muestra coagulada.  ")
    assert remuestreos.listar(1)[0].detalle == "Muestra coagulada."


@pytest.mark.parametrize(
    "recorrido",
    [None, (), HACIA_COREA[1:3], HACIA_EL_ANALISIS[1:]],
    ids=["TurnoSacado", "ListoParaRetirar", "EnLaboratorioCentral", "EnAnalisis"],
)
def test_solo_se_pide_desde_viaje_a_corea_o_area_de_bioinformatica(
    client, entorno, remuestreos, recorrido
):
    estudios, _, _ = entorno
    if recorrido is not None:
        notificar(client, 3)  # ListoParaRetirar
        llevar_a(estudios, recorrido)
    r = pedir(client)
    assert r.status_code == 409
    assert r.json()["code"] == "estudio_sin_remuestreo_posible"
    assert remuestreos.listar(1) == []


@pytest.mark.parametrize("motivo", ["volumen_menor_2ml", "otro", ""])
def test_el_motivo_tiene_que_ser_uno_de_los_dos_validos(client, en_corea, remuestreos, motivo):
    r = pedir(client, motivo=motivo)
    assert r.status_code == 422
    assert remuestreos.listar(1) == []
    assert en_corea[0].obtener(1).estado == EstadoEstudio.EN_VIAJE_A_COREA


def test_el_administrativo_tambien_puede_pedirlo_por_adn_insuficiente(
    client, en_corea, remuestreos
):
    estudios, _, avisos = en_corea

    r = pedir(client, "El laboratorio de Corea informó ADN degradado.", motivo=MOTIVO_ADN)

    assert r.status_code == 200
    assert r.json()["motivo"] == MOTIVO_ADN
    assert "ADN" in avisos.para(LUCIA)[0]
    assert "mala calidad" not in avisos.para(LUCIA)[0]
    assert remuestreos.listar(1)[0].motivo == MOTIVO_ADN
    assert estudios.obtener(1).estado == EstadoEstudio.TURNO_SACADO


def test_si_ya_hay_un_remuestreo_pendiente_no_se_pide_otro(client, en_corea, remuestreos):
    estudios, _, avisos = en_corea
    remuestreos.registrar(1, MOTIVO_ADN, "Pedido anterior", AHORA)

    r = pedir(client)

    assert r.status_code == 409
    assert r.json()["code"] == "remuestreo_pendiente"
    assert len(remuestreos.listar(1)) == 1
    assert estudios.obtener(1).estado == EstadoEstudio.EN_VIAJE_A_COREA
    assert avisos.enviados == []


def test_un_remuestreo_ya_resuelto_no_impide_pedir_otro(client, en_corea, remuestreos):
    remuestreos.registrar(1, MOTIVO_ADN, "Pedido anterior", AHORA)
    remuestreos.resolver(1, AHORA)

    assert pedir(client).status_code == 200
    assert len(remuestreos.listar(1)) == 2


def test_un_estudio_inexistente_da_404(client, entorno):
    assert pedir(client, estudio=99).status_code == 404


def test_solo_el_administrativo_pide_el_remuestreo(client, en_corea, login_as, remuestreos):
    for rol in (Rol.PACIENTE, Rol.BIOINFORMATICO, Rol.MEDICO_TRATANTE, Rol.TRANSPORTISTA):
        login_as(rol, email=LUCIA)
        assert pedir(client).status_code == 403
    assert remuestreos.listar(1) == []
    assert en_corea[0].obtener(1).estado == EstadoEstudio.EN_VIAJE_A_COREA


# --- the studies on which it can be asked -------------------------------------------------------


def test_sin_estudios_en_corea_ni_en_bioinformatica_la_lista_esta_vacia(client, entorno):
    assert remuestreables(client) == []


def test_lista_el_estudio_en_viaje_a_corea_con_su_paciente_y_su_dni(client, en_corea):
    assert remuestreables(client) == [
        {
            "estudio_id": 1,
            "paciente": "Lucía Fernández",
            "dni": "30111222",
            "estado": "EnViajeACorea",
            "remuestreo_pendiente": None,
        }
    ]


def test_lista_los_estudios_de_los_dos_estados_en_orden_y_ningun_otro(client, en_corea):
    estudios = en_corea[0]
    llevar_a(estudios, [EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA])
    # study 3 travels too, and study 2 stays in Creado
    llevar_a(estudios, [EstadoEstudio.PAGADO, EstadoEstudio.TURNO_SACADO, *HACIA_COREA], estudio=3)

    lista = remuestreables(client)

    assert [(e["estudio_id"], e["estado"]) for e in lista] == [
        (1, "EnElAreaDeBioinformatica"),
        (3, "EnViajeACorea"),
    ]


def test_un_estudio_que_ya_paso_a_analisis_no_se_lista(client, en_corea):
    llevar_a(
        en_corea[0],
        [
            EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA,
            EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO,
        ],
    )

    assert remuestreables(client) == []


def test_la_lista_muestra_el_remuestreo_pendiente_si_lo_hay(client, en_corea, remuestreos):
    remuestreos.registrar(1, MOTIVO_ADN, "Pedido anterior", AHORA, "u-otro")

    (estudio,) = remuestreables(client)

    pendiente = estudio["remuestreo_pendiente"]
    assert (pendiente["motivo"], pendiente["detalle"]) == (MOTIVO_ADN, "Pedido anterior")
    assert pendiente["remuestreo_id"] == 1
    assert pendiente["pedido_en"].startswith("2026-11-02T10:07")


def test_un_remuestreo_resuelto_no_aparece_como_pendiente(client, en_corea, remuestreos):
    remuestreos.registrar(1, MOTIVO_ADN, "Pedido anterior", AHORA)
    remuestreos.resolver(1, AHORA)

    assert remuestreables(client)[0]["remuestreo_pendiente"] is None


def test_solo_el_administrativo_ve_la_lista(client, en_corea, login_as):
    for rol in (Rol.PACIENTE, Rol.BIOINFORMATICO, Rol.MEDICO_TRATANTE, Rol.TRANSPORTISTA):
        login_as(rol, email=LUCIA)
        assert client.get("/turnos/estudios/remuestreables").status_code == 403


# --- the states and the reasons agree with the rest of the code ---------------------------------


def test_los_estados_de_la_lista_son_los_que_la_transicion_nueva_permite():
    assert ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO == {
        EstadoEstudio.EN_VIAJE_A_COREA,
        EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA,
    }
    for estado in ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO:
        assert can_transition(estado, EstadoEstudio.TURNO_SACADO)


def test_los_motivos_del_endpoint_son_los_de_las_reglas():
    motivo = RemuestreoAdministrativoEntrada.model_fields["motivo"].annotation
    assert set(get_args(motivo)) == set(MOTIVOS_REMUESTREO)
    assert set(CAUSAS_DE_REMUESTREO) == set(MOTIVOS_REMUESTREO)


# --- the patient books again -------------------------------------------------------------------


def test_el_paciente_queda_habilitado_para_un_nuevo_turno_hasta_que_lo_reserva(
    client, en_corea, remuestreos, login_as
):
    pedir(client)
    login_as(Rol.PACIENTE, email=LUCIA)
    pendientes = client.get("/turnos/habilitados").json()
    assert pendientes == [
        {
            "estudio_id": 1,
            "estado": "TurnoSacado",
            "motivo": "nueva_reserva",
            "inasistencias": 0,
            "remuestreo_motivo": MOTIVO_CALIDAD,
        }
    ]
    # if the patient does not book, the study stays stopped and the notice stays pending
    assert client.get("/turnos/habilitados").json() == pendientes

    reservar(client, OTRO_INICIO)
    assert client.get("/turnos/habilitados").json() == []
    assert en_corea[0].obtener(1).estado == EstadoEstudio.TURNO_SACADO
    assert remuestreos.pendiente(1) is None
    assert remuestreos.listar(1)[0].resuelto is True
    assert en_corea[0].asientos == []  # no new charge


def test_cancelar_el_turno_de_un_remuestreo_no_devuelve_el_estudio_a_pagado(
    client, en_corea, login_as
):
    pedir(client)
    login_as(Rol.PACIENTE, email=LUCIA)
    nuevo = reservar(client, OTRO_INICIO)
    r = client.post(f"/turnos/{nuevo['id']}/cancelar")
    assert r.status_code == 200
    assert r.json()["estudio_estado"] == "TurnoSacado"
    assert client.get("/turnos/habilitados").json()[0]["motivo"] == "nueva_reserva"


def test_se_puede_repetir_el_ciclo_si_la_segunda_muestra_tambien_llega_mal(
    client, en_corea, remuestreos, login_as
):
    estudios = en_corea[0]
    pedir(client)
    login_as(Rol.PACIENTE, email=LUCIA)
    reservar(client, OTRO_INICIO)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)
    app.dependency_overrides[reglas.ahora] = lambda: OTRO_INICIO.replace(minute=40)
    assert notificar(client, 1.9).status_code == 200
    llevar_a(estudios, HACIA_COREA[1:])
    assert pedir(client, "Otra vez en mal estado.").status_code == 200
    assert [r.detalle for r in remuestreos.listar(1)] == [MOTIVO, "Otra vez en mal estado."]


# --- DNA not enough, reported by the bioinformatician (it stays a valid path) -----------------


@pytest.fixture
def en_analisis(client, entorno, login_as):
    estudios, turnos, avisos = entorno
    notificar(client, 3)
    llevar_a(estudios, HACIA_EL_ANALISIS[1:])
    avisos.enviados.clear()
    login_as(Rol.BIOINFORMATICO)
    return estudios, turnos, avisos


def test_con_adn_insuficiente_el_bioinformatico_habilita_el_remuestreo(
    client, en_analisis, remuestreos
):
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
    assert remuestreos.listar(1)[0].motivo == MOTIVO_ADN


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
