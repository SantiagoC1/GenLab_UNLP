"""Payment of a study through Mercado Pago: the charge and the confirmation when the patient comes back.

Memory repositories and a fake Mercado Pago. The installments are chosen and managed by Mercado
Pago: the platform receives one payment, approved or not.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.integrations.cupones import CuponesSimulador, obtener_cupones
from app.integrations.mercadopago import obtener_mercadopago
from app.main import app
from app.modules.cupones.repositorio import Cupon
from app.modules.cupones.repositorio import obtener_repositorio as obtener_repositorio_cupones
from app.modules.cupones.repositorio_memoria import RepositorioCuponesEnMemoria
from app.modules.presupuesto_pago.mercadopago import MercadoPagoConfig
from app.modules.presupuesto_pago.repositorio import obtener_repositorio
from app.modules.presupuesto_pago.repositorio_memoria import RepositorioEstudiosEnMemoria
from app.modules.presupuesto_pago.router import obtener_config_mercadopago
from tests.fakes import AvisosEspia, MercadoPagoFalso

LUCIA = "lucia.fernandez@example.com"
# 1 USD is 2 units of the currency of the charge: the converted amount is easy to tell.
CONFIG = MercadoPagoConfig(
    frontend_url="http://localhost:5173",
    currency_id="ARS",
    usd_rate=Decimal("2"),
    max_installments=6,
)
PAY = "/presupuesto_pago/mis-estudios"
CONFIRM = "/presupuesto_pago/pago-mercadopago/confirmar"


@pytest.fixture
def entorno(login_as):
    """Lucía has a 500 USD budget (study 1) and the coupon CUP-0001 (20%) from her doctor."""
    integracion_cupones.reiniciar_simulador()
    estudios = RepositorioEstudiosEnMemoria()
    estudios.guardar_presupuesto(1, 500, datetime.now(UTC))
    estudios.guardar_presupuesto(2, 590, datetime.now(UTC))
    cupones = RepositorioCuponesEnMemoria()
    CuponesSimulador().obtener_cupones(20, 1)
    cupones.guardar_nuevos([Cupon("CUP-0001", 20, "Vigente", datetime.now(UTC), None, LUCIA)])
    avisos = AvisosEspia()
    mercadopago = MercadoPagoFalso()
    app.dependency_overrides[obtener_repositorio] = lambda: estudios
    app.dependency_overrides[obtener_repositorio_cupones] = lambda: cupones
    app.dependency_overrides[obtener_cupones] = CuponesSimulador
    app.dependency_overrides[obtener_avisos] = lambda: avisos
    app.dependency_overrides[obtener_mercadopago] = lambda: mercadopago
    app.dependency_overrides[obtener_config_mercadopago] = lambda: CONFIG
    login_as(Rol.PACIENTE, email=LUCIA)
    yield estudios, cupones, avisos, mercadopago
    integracion_cupones.reiniciar_simulador()


def checkout(client, estudio=1):
    return client.post(f"{PAY}/{estudio}/pago-mercadopago")


def confirm(client, payment_id="1001"):
    return client.post(CONFIRM, json={"payment_id": payment_id})


# --- the charge ---------------------------------------------------------------------------------


def test_the_charge_has_the_budget_amount_the_installments_and_the_way_back(client, entorno):
    estudios, _, _, mercadopago = entorno

    r = checkout(client)

    assert r.status_code == 201, r.text
    assert r.json() == {
        "estudio_id": 1,
        "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=PREF-1",
        "preference_id": "PREF-1",
        "importe_original_usd": 500,
        "importe_usd": 500,
        "cupon": None,
        "moneda": "ARS",
        "importe": 1000.0,
        "cuotas_maximas": 6,
    }
    (preference,) = mercadopago.preferences
    assert preference["external_reference"] == "genlab-study-1"
    assert preference["amount"] == Decimal("1000.00")
    assert preference["currency_id"] == "ARS"
    assert preference["max_installments"] == 6
    return_url = "http://localhost:5173/paciente/pago-resultado"
    assert preference["back_urls"] == {
        "success": return_url,
        "pending": return_url,
        "failure": return_url,
    }
    # Creating the charge pays nothing.
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO
    assert estudios.asientos == []


def test_the_charge_uses_the_amount_with_the_coupon_applied(client, entorno):
    _, _, _, mercadopago = entorno
    client.post(f"{PAY}/1/cupon", json={"codigo": "CUP-0001"})

    r = checkout(client)

    assert r.status_code == 201
    assert (r.json()["importe_original_usd"], r.json()["importe_usd"]) == (500, 400)
    assert r.json()["cupon"] == "CUP-0001"
    assert r.json()["importe"] == 800.0
    assert mercadopago.preferences[0]["amount"] == Decimal("800.00")


def test_a_study_that_cannot_be_paid_has_no_charge(client, entorno):
    estudios, _, _, mercadopago = entorno
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, datetime.now(UTC))

    already_paid = checkout(client)
    other_patient = checkout(client, estudio=3)
    missing = checkout(client, estudio=99)

    assert already_paid.status_code == 409
    assert already_paid.json()["code"] == "estudio_ya_pago"
    assert other_patient.status_code == 404
    assert missing.status_code == 404
    assert mercadopago.preferences == []


def test_a_study_without_budget_has_no_charge(client, entorno):
    # Study 3 (Sofía's) has no budget and belongs to someone else: Lucía only sees 404.
    estudios, _, _, mercadopago = entorno
    estudios.estudios[1].presupuesto_importe_usd = None

    r = checkout(client)

    assert r.status_code == 409
    assert mercadopago.preferences == []


def test_when_mercado_pago_is_down_there_is_no_charge_and_nothing_changes(client, entorno):
    estudios, _, _, mercadopago = entorno
    mercadopago.fail_create = True

    r = checkout(client)

    assert r.status_code == 503
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO


# --- the patient comes back: approved ------------------------------------------------------------


def test_an_approved_payment_is_recorded_with_its_installments_and_the_study_is_paid(
    client, entorno
):
    estudios, _, avisos, mercadopago = entorno
    mercadopago.add_payment("1001", installments=3, installment_amount="333.33")
    avisos.enviados.clear()

    r = confirm(client)

    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["resultado"], body["estado_estudio"], body["estado_mp"]) == (
        "aprobado",
        "Pagado",
        "approved",
    )
    assert (body["importe_original_usd"], body["importe_usd"]) == (500, 500)
    assert (body["cuotas"], body["valor_cuota"], body["moneda"]) == (3, 333.33, "ARS")
    assert body["metodo"] == "mercadopago_credit_card"
    assert body["mp_payment_id"] == "1001"
    assert body["paciente_avisado"] is True

    assert estudios.obtener(1).estado == EstadoEstudio.PAGADO
    (asiento,) = estudios.asientos
    assert (asiento.importe_usd, asiento.metodo, asiento.cupon) == (
        500,
        "mercadopago_credit_card",
        None,
    )
    assert (asiento.cuotas, asiento.valor_cuota, asiento.mp_payment_id) == (3, 333.33, "1001")
    assert "Recibimos el pago" in avisos.para(LUCIA)[0]
    assert mercadopago.queries == ["1001"]


def test_an_approved_payment_with_a_coupon_marks_the_coupon_as_used(client, entorno):
    estudios, cupones, _, mercadopago = entorno
    client.post(f"{PAY}/1/cupon", json={"codigo": "CUP-0001"})
    mercadopago.add_payment("1001", amount="800.00", installments=2, installment_amount="400.00")

    r = confirm(client)

    assert r.status_code == 200, r.text
    assert (r.json()["importe_original_usd"], r.json()["importe_usd"]) == (500, 400)
    assert r.json()["cupon"] == "CUP-0001"
    assert cupones.obtener("CUP-0001").estado == "Usado"
    assert integracion_cupones._EMITIDOS["CUP-0001"]["estado"] == "Usado"
    assert estudios.asientos[0].cupon == "CUP-0001"


def test_without_the_value_of_the_installment_it_is_the_amount_over_the_installments(
    client, entorno
):
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001", installments=4, installment_amount=None)

    assert confirm(client).status_code == 200

    assert estudios.asientos[0].valor_cuota == 250.0


# --- the patient comes back: pending and rejected ------------------------------------------------


@pytest.mark.parametrize("status", ["pending", "in_process", "authorized", "in_mediation"])
def test_a_pending_payment_records_nothing_as_paid(client, entorno, status):
    estudios, cupones, avisos, mercadopago = entorno
    client.post(f"{PAY}/1/cupon", json={"codigo": "CUP-0001"})
    mercadopago.add_payment(
        "1001", status=status, amount="800.00", detail="pending_waiting_payment"
    )
    avisos.enviados.clear()

    r = confirm(client)

    assert r.status_code == 200
    assert (r.json()["resultado"], r.json()["estado_mp"]) == ("pendiente", status)
    assert r.json()["estado_estudio"] == "Creado"
    assert r.json()["importe_usd"] is None and r.json()["cuotas"] is None
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO
    assert estudios.asientos == []
    assert cupones.obtener("CUP-0001").estado == "Vigente"
    assert avisos.enviados == []


def test_a_pending_payment_that_is_later_approved_is_recorded_then(client, entorno):
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001", status="pending")
    assert confirm(client).json()["resultado"] == "pendiente"

    mercadopago.add_payment("1001", status="approved")
    r = confirm(client)

    assert r.json()["resultado"] == "aprobado"
    assert len(estudios.asientos) == 1
    assert estudios.obtener(1).estado == EstadoEstudio.PAGADO


@pytest.mark.parametrize("status", ["rejected", "cancelled", "refunded", "charged_back"])
def test_a_rejected_payment_records_nothing_and_the_patient_can_try_again(client, entorno, status):
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment(
        "1001", status=status, detail="cc_rejected_insufficient_amount", installments=1
    )

    r = confirm(client)

    assert r.status_code == 200
    assert (r.json()["resultado"], r.json()["estado_mp"]) == ("rechazado", status)
    assert r.json()["detalle_mp"] == "cc_rejected_insufficient_amount"
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO
    assert estudios.asientos == []
    # Trying again: a new charge for the same study.
    assert checkout(client).status_code == 201
    assert len(mercadopago.preferences) == 1


# --- confirming the same payment twice -----------------------------------------------------------


def test_confirming_the_same_payment_twice_does_not_repeat_anything(client, entorno):
    estudios, cupones, avisos, mercadopago = entorno
    client.post(f"{PAY}/1/cupon", json={"codigo": "CUP-0001"})
    mercadopago.add_payment("1001", amount="800.00", installments=2, installment_amount="400.00")
    avisos.enviados.clear()

    first = confirm(client)
    second = confirm(client)

    assert first.status_code == second.status_code == 200
    assert second.json()["resultado"] == "aprobado"
    for field in (
        "importe_usd",
        "importe_original_usd",
        "cuotas",
        "valor_cuota",
        "metodo",
        "cupon",
    ):
        assert second.json()[field] == first.json()[field]
    assert second.json()["paciente_avisado"] is False
    assert len(estudios.asientos) == 1
    assert len(avisos.para(LUCIA)) == 1
    history = [(c.desde, c.hacia) for c in estudios.obtener(1).historial]
    assert history.count((EstadoEstudio.CREADO, EstadoEstudio.PAGADO)) == 1
    assert cupones.obtener("CUP-0001").estado == "Usado"


def test_a_payment_recorded_but_with_the_study_still_unpaid_is_completed(client, entorno):
    # It failed between the record and the change of state: confirming again finishes the job.
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001")
    estudios.registrar_asiento(
        estudios.obtener(1),
        500,
        "mercadopago_credit_card",
        datetime.now(UTC),
        None,
        3,
        333.33,
        "1001",
    )

    r = confirm(client)

    assert r.status_code == 200
    assert r.json()["resultado"] == "aprobado"
    assert estudios.obtener(1).estado == EstadoEstudio.PAGADO
    assert len(estudios.asientos) == 1


def test_two_confirmations_at_once_leave_one_payment(client, entorno, monkeypatch):
    # The other confirmation recorded the payment between the check and the insert.
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001")
    original = estudios.registrar_asiento

    def lost_the_race(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("duplicate key value violates unique constraint")

    monkeypatch.setattr(estudios, "registrar_asiento", lost_the_race)

    r = confirm(client)

    assert r.status_code == 200
    assert r.json()["resultado"] == "aprobado"
    assert len(estudios.asientos) == 1


# --- what is not accepted ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("amount", "currency"),
    [("999.00", "ARS"), ("1000.01", "ARS"), ("500.00", "ARS"), ("1000.00", "USD")],
)
def test_a_payment_whose_amount_does_not_match_is_not_recorded(client, entorno, amount, currency):
    estudios, cupones, avisos, mercadopago = entorno
    mercadopago.add_payment("1001", amount=amount, currency=currency)
    avisos.enviados.clear()

    r = confirm(client)

    assert r.status_code == 409
    assert r.json()["code"] == "monto_no_coincide"
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO
    assert estudios.asientos == []
    assert avisos.enviados == []


def test_the_amount_must_match_the_coupon_applied(client, entorno):
    # The coupon lowers the amount to 800: paying the full 1000 is not what was asked.
    estudios, cupones, _, mercadopago = entorno
    client.post(f"{PAY}/1/cupon", json={"codigo": "CUP-0001"})
    mercadopago.add_payment("1001", amount="1000.00")

    r = confirm(client)

    assert r.json()["code"] == "monto_no_coincide"
    assert cupones.obtener("CUP-0001").estado == "Vigente"
    assert estudios.asientos == []


def test_a_payment_of_the_study_of_someone_else_looks_like_a_missing_one(client, entorno):
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001", reference="genlab-study-3")

    r = confirm(client)

    assert r.status_code == 404
    assert estudios.asientos == []


@pytest.mark.parametrize("reference", [None, "", "study-1", "genlab-study-x", "genlab-study-1-2"])
def test_a_payment_with_a_reference_of_another_system_is_refused(client, entorno, reference):
    mercadopago = entorno[3]
    mercadopago.add_payment("1001", reference=reference)

    r = confirm(client)

    assert r.status_code == 409
    assert r.json()["code"] == "referencia_invalida"
    assert entorno[0].asientos == []


def test_an_unknown_payment_is_a_404(client, entorno):
    r = confirm(client, "777")

    assert r.status_code == 404
    assert r.json()["code"] == "pago_inexistente"


def test_when_mercado_pago_does_not_answer_nothing_is_recorded(client, entorno):
    estudios, _, _, mercadopago = entorno
    mercadopago.add_payment("1001")
    mercadopago.fail_get = True

    r = confirm(client)

    assert r.status_code == 503
    assert estudios.asientos == []
    assert estudios.obtener(1).estado == EstadoEstudio.CREADO


def test_an_approved_payment_for_a_study_that_is_already_paid_is_not_recorded_again(
    client, entorno
):
    estudios, _, _, mercadopago = entorno
    estudios.cambiar_estado(1, EstadoEstudio.PAGADO, datetime.now(UTC))
    mercadopago.add_payment("1001")

    r = confirm(client)

    assert r.status_code == 409
    assert r.json()["code"] == "estudio_ya_pago"
    assert estudios.asientos == []


@pytest.mark.parametrize("payment_id", ["", "../x", "1001 OR 1=1", "a" * 65])
def test_the_payment_id_has_to_look_like_one(client, entorno, payment_id):
    assert confirm(client, payment_id).status_code == 422
    assert entorno[3].queries == []


def test_only_the_patient_pays(client, entorno, login_as):
    for rol in (Rol.ADMINISTRATIVO_LABORATORIO, Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO):
        login_as(rol, email=LUCIA)
        assert checkout(client).status_code == 403
        assert confirm(client).status_code == 403
    assert entorno[3].preferences == [] and entorno[3].queries == []


def test_the_financial_record_shows_the_installments(client, entorno, login_as):
    entorno[3].add_payment("1001", installments=3, installment_amount="333.33")
    confirm(client)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO)

    r = client.get("/presupuesto_pago/registro-financiero")

    assert r.status_code == 200, r.text
    (asiento,) = r.json()
    assert (asiento["cuotas"], asiento["valor_cuota"], asiento["mp_payment_id"]) == (
        3,
        333.33,
        "1001",
    )
