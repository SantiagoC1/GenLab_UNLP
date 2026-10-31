from datetime import UTC, datetime

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.integrations.cupones import CuponesSimulador, obtener_cupones
from app.main import app
from app.modules.cupones.repositorio import Cupon, RepositorioCuponesEnMemoria
from app.modules.cupones.repositorio import obtener_repositorio as obtener_repositorio_cupones
from app.modules.cupones.servicio import documento_pdf
from app.modules.presupuesto_pago.paciente import importe_con_descuento
from app.modules.presupuesto_pago.repositorio import (
    RepositorioEstudiosEnMemoria,
    obtener_repositorio,
)
from tests.fakes import AvisosEspia

LUCIA = "lucia.fernandez@example.com"
PDF = {"Content-Type": "application/pdf"}


class CuponesCaidoAlUsar(CuponesSimulador):
    def marcar_cupon_usado(self, codigo: str) -> dict:
        raise ConnectionError("sin servicio")


class CuponesCaidoAlValidar(CuponesSimulador):
    def validar_cupon(self, codigo: str) -> dict:
        raise ConnectionError("sin servicio")


@pytest.fixture
def entorno(login_as):
    """Lucía has a 500 USD budget and the coupon CUP-0001 (20%) from her doctor."""
    integracion_cupones.reiniciar_simulador()
    estudios = RepositorioEstudiosEnMemoria()
    estudios.guardar_presupuesto(1, 500, datetime.now(UTC))
    estudios.guardar_presupuesto(2, 590, datetime.now(UTC))
    cupones = RepositorioCuponesEnMemoria()
    CuponesSimulador().obtener_cupones(20, 2)
    ahora = datetime.now(UTC)
    cupones.guardar_nuevos(
        [
            Cupon("CUP-0001", 20, "Vigente", ahora, "ana.perez@example.com", LUCIA),
            Cupon("CUP-0002", 20, "Vigente", ahora, "ana.perez@example.com", "otro@example.com"),
        ]
    )
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_cupones] = lambda: cupones
    app.dependency_overrides[obtener_cupones] = CuponesSimulador
    app.dependency_overrides[obtener_avisos] = AvisosEspia
    login_as(Rol.PACIENTE, email=LUCIA)
    yield estudios, cupones
    integracion_cupones.reiniciar_simulador()


def aplicar(client, codigo="CUP-0001", estudio=1):
    return client.post(f"/presupuesto_pago/mis-estudios/{estudio}/cupon", json={"codigo": codigo})


def pagar(client, estudio=1):
    return client.post(
        f"/presupuesto_pago/mis-estudios/{estudio}/pago", json={"metodo": "tarjeta_debito"}
    )


def test_el_descuento_se_redondea_a_dolares_enteros():
    assert importe_con_descuento(500, 20) == 400
    assert importe_con_descuento(590, 20) == 472
    assert importe_con_descuento(500, 100) == 0
    assert importe_con_descuento(500, 0) == 500


def test_aplicar_un_cupon_vigente_muestra_el_nuevo_importe(client, entorno):
    r = aplicar(client)
    assert r.status_code == 200
    assert r.json() == {
        "codigo": "CUP-0001",
        "descuento": 20,
        "importe_original_usd": 500,
        "importe_con_descuento_usd": 400,
    }
    mis = client.get("/presupuesto_pago/mis-estudios").json()[0]
    assert mis["importe_usd"] == 500
    assert mis["cupon_aplicado"]["importe_con_descuento_usd"] == 400


def test_se_puede_adjuntar_el_pdf_del_cupon(client, entorno):
    pdf = documento_pdf(entorno[1].obtener("CUP-0001"))
    r = client.post("/presupuesto_pago/mis-estudios/1/cupon-pdf", content=pdf, headers=PDF)
    assert r.status_code == 200
    assert r.json()["codigo"] == "CUP-0001"
    assert r.json()["importe_con_descuento_usd"] == 400


def test_un_archivo_que_no_es_pdf_se_rechaza(client, entorno):
    r = client.post("/presupuesto_pago/mis-estudios/1/cupon-pdf", content=b"CUP-0001", headers=PDF)
    assert r.status_code == 422
    assert r.json()["code"] == "archivo_no_pdf"
    assert entorno[0].obtener(1).cupon_aplicado is None


def test_un_pdf_sin_codigo_se_rechaza(client, entorno):
    r = client.post(
        "/presupuesto_pago/mis-estudios/1/cupon-pdf", content=b"%PDF-1.4 nada", headers=PDF
    )
    assert r.status_code == 422
    assert r.json()["code"] == "cupon_sin_codigo"
    r = client.post("/presupuesto_pago/mis-estudios/1/cupon-pdf", content=b"", headers=PDF)
    assert r.status_code == 422


def test_un_cupon_que_no_esta_vigente_muestra_el_motivo_y_mantiene_el_importe(client, entorno):
    CuponesSimulador().marcar_cupon_usado("CUP-0001")
    r = aplicar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_vigente"
    assert "Usado" in r.json()["detalle"]
    assert entorno[0].obtener(1).cupon_aplicado is None
    assert client.get("/presupuesto_pago/mis-estudios").json()[0]["importe_usd"] == 500


def test_un_cupon_que_no_existe_no_se_aplica(client, entorno):
    r = aplicar(client, "CUP-4040")
    assert r.status_code == 409
    assert "Inexistente" in r.json()["detalle"]


def test_un_cupon_asignado_a_otro_paciente_no_se_aplica(client, entorno):
    r = aplicar(client, "CUP-0002")
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_de_otro_paciente"


def test_si_el_modulo_de_cupones_no_responde_no_se_aplica(client, entorno):
    app.dependency_overrides[obtener_cupones] = CuponesCaidoAlValidar
    assert aplicar(client).status_code == 503


def test_pagar_con_cupon_cobra_el_nuevo_importe_e_informa_el_uso(client, entorno):
    estudios, cupones = entorno
    aplicar(client)
    r = pagar(client)
    assert r.status_code == 201
    assert r.json()["importe_original_usd"] == 500
    assert r.json()["importe_usd"] == 400
    assert r.json()["cupon"] == "CUP-0001"
    assert r.json()["cupon_informado"] is True

    (asiento,) = estudios.asientos
    assert (asiento.importe_usd, asiento.cupon) == (400, "CUP-0001")
    assert CuponesSimulador().validar_cupon("CUP-0001")["estado"] == "Usado"
    assert cupones.obtener("CUP-0001").estado == "Usado"
    assert estudios.obtener(1).estado == EstadoEstudio.PAGADO


def test_un_cupon_cien_por_ciento_deja_el_pago_en_cero(client, entorno):
    estudios, cupones = entorno
    cupones.cupones["CUP-0001"].descuento = 100
    integracion_cupones._EMITIDOS["CUP-0001"]["descuento"] = 100
    aplicar(client)
    assert pagar(client).json()["importe_usd"] == 0
    assert estudios.asientos[0].importe_usd == 0


def test_si_el_cupon_se_uso_antes_de_pagar_se_cobra_el_importe_original_despues(client, entorno):
    estudios, _ = entorno
    aplicar(client)
    CuponesSimulador().marcar_cupon_usado("CUP-0001")
    r = pagar(client)
    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_vigente"
    assert estudios.asientos == []
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO
    assert estudios.obtener(1).cupon_aplicado is None
    # the patient can now pay the original amount
    assert pagar(client).json()["importe_usd"] == 500


def test_si_no_se_puede_informar_el_uso_no_se_registra_el_pago(client, entorno):
    estudios, _ = entorno
    aplicar(client)
    app.dependency_overrides[obtener_cupones] = CuponesCaidoAlUsar
    # the validation still answers because only marking the use is down
    r = pagar(client)
    assert r.status_code == 503
    assert estudios.asientos == []
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO


def test_quitar_el_cupon_vuelve_al_importe_original(client, entorno):
    aplicar(client)
    r = client.delete("/presupuesto_pago/mis-estudios/1/cupon")
    assert r.status_code == 200
    assert r.json()["cupon_aplicado"] is None
    assert pagar(client).json()["importe_usd"] == 500


def test_no_se_aplica_un_cupon_a_un_estudio_que_ya_no_se_puede_pagar(client, entorno):
    pagar(client)
    assert aplicar(client).status_code == 409


def test_solo_el_paciente_aplica_cupones(client, entorno, login_as):
    login_as(Rol.MEDICO_TRATANTE)
    assert aplicar(client).status_code == 403
