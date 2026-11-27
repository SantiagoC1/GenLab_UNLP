"""The payment through Mercado Pago on the database repositories (the fake Supabase client).

No repository is overridden: what is stored in `payments`, `coupons` and the history of the states
is what the real wiring writes.
"""

from decimal import Decimal

import pytest

from app.core.enums import Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.integrations.mercadopago import obtener_mercadopago
from app.main import app
from app.modules.presupuesto_pago.mercadopago import MercadoPagoConfig
from app.modules.presupuesto_pago.router import obtener_config_mercadopago
from tests.fake_supabase import FakeSupabase
from tests.fakes import AvisosEspia, MercadoPagoFalso

ADMIN_ID = "u-admin"
PATIENT_ID = "9b1f6a52-0c1d-4e62-8f7a-2f0f4a5d9c11"
PATIENT_MAIL = "paula.ramos@example.com"
CONFIG = MercadoPagoConfig(
    frontend_url="http://localhost:5173",
    currency_id="ARS",
    usd_rate=Decimal("2"),
    max_installments=6,
)
PAY = "/presupuesto_pago/mis-estudios/4"
CONFIRM = "/presupuesto_pago/pago-mercadopago/confirmar"


@pytest.fixture
def db(monkeypatch):
    """Paula's study 4 has its 500 USD budget, and she holds the coupon CUP-0002 (20%)."""
    fake = FakeSupabase(
        users=[
            {"id": ADMIN_ID, "email": "admin@example.com", "role": Rol.ADMINISTRATIVO_LABORATORIO},
            {"id": "u-doctor", "email": "ana.perez@example.com", "role": Rol.MEDICO_TRATANTE},
            {"id": "u-paula", "email": PATIENT_MAIL, "role": Rol.PACIENTE},
        ],
        patients=[
            {
                "id": PATIENT_ID,
                "account_user_id": "u-paula",
                "first_name": "Paula",
                "last_name": "Ramos",
            }
        ],
        studies=[
            {"id": 4, "patient_id": PATIENT_ID, "requested_by": "u-doctor", "state": "Creado"}
        ],
        study_genes=[{"study_id": 4, "gene": gene} for gene in ("GBA", "GLA", "IDUA")],
        study_state_history=[
            {"study_id": 4, "from_state": None, "to_state": "Creado", "changed_by": "u-doctor"}
        ],
        budgets=[
            {
                "study_id": 4,
                "gene_count": 3,
                "amount_usd": 500,
                "issued_by": ADMIN_ID,
                "applied_coupon_code": None,
                "applied_coupon_pct": None,
            }
        ],
        coupons=[
            {
                "code": "CUP-0002",
                "discount_pct": 20,
                "status": "Vigente",
                "doctor_id": "u-doctor",
                "patient_id": PATIENT_ID,
            }
        ],
    )
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    monkeypatch.setattr("app.modules.consulta_medica.repository.supabase_admin", fake)
    integracion_cupones.reiniciar_simulador()
    yield fake
    integracion_cupones.reiniciar_simulador()


@pytest.fixture
def mercadopago(login_as):
    fake = MercadoPagoFalso()
    app.dependency_overrides[obtener_mercadopago] = lambda: fake
    app.dependency_overrides[obtener_config_mercadopago] = lambda: CONFIG
    app.dependency_overrides[obtener_avisos] = AvisosEspia
    login_as(Rol.PACIENTE, id="u-paula", email=PATIENT_MAIL)
    return fake


def confirm(client, payment_id="1001"):
    return client.post(CONFIRM, json={"payment_id": payment_id})


def test_an_approved_payment_is_stored_with_its_installments_and_the_study_is_paid(
    client, db, mercadopago
):
    client.post(f"{PAY}/cupon", json={"codigo": "CUP-0002"})
    mercadopago.add_payment(
        "5551234",
        reference="genlab-study-4",
        amount="800.00",
        installments=3,
        installment_amount="266.67",
    )

    r = confirm(client, "5551234")

    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "aprobado"
    (payment,) = db.rows("payments")
    assert payment["study_id"] == 4
    assert payment["amount_usd"] == 400
    assert payment["method"] == "mercadopago_credit_card"
    assert payment["coupon_code"] == "CUP-0002"
    assert payment["installments"] == 3
    assert payment["installment_amount"] == 266.67
    assert payment["mp_payment_id"] == "5551234"
    coupon = db.rows("coupons")[0]
    assert payment["coupon_id"] == coupon["id"]
    assert coupon["status"] == "Usado"
    assert db.rows("studies")[0]["state"] == "Pagado"
    last = db.rows("study_state_history")[-1]
    assert (last["from_state"], last["to_state"], last["changed_by"]) == (
        "Creado",
        "Pagado",
        "u-paula",
    )


def test_confirming_twice_leaves_one_row_and_one_change_of_state(client, db, mercadopago):
    mercadopago.add_payment("5551234", reference="genlab-study-4", amount="1000.00")

    first = confirm(client, "5551234")
    second = confirm(client, "5551234")

    assert first.status_code == second.status_code == 200
    assert second.json()["resultado"] == "aprobado"
    assert second.json()["mp_payment_id"] == "5551234"
    assert len(db.rows("payments")) == 1
    changes = [r for r in db.rows("study_state_history") if r["to_state"] == "Pagado"]
    assert len(changes) == 1


def test_a_second_payment_for_the_same_study_is_refused(client, db, mercadopago):
    mercadopago.add_payment("1", reference="genlab-study-4", amount="1000.00")
    mercadopago.add_payment("2", reference="genlab-study-4", amount="1000.00")
    confirm(client, "1")

    r = confirm(client, "2")

    assert r.status_code == 409
    assert r.json()["code"] == "estudio_ya_pago"
    assert len(db.rows("payments")) == 1


@pytest.mark.parametrize("status", ["pending", "in_process", "rejected"])
def test_a_payment_that_is_not_approved_stores_nothing(client, db, mercadopago, status):
    client.post(f"{PAY}/cupon", json={"codigo": "CUP-0002"})
    mercadopago.add_payment("5551234", status=status, reference="genlab-study-4", amount="800.00")

    r = confirm(client, "5551234")

    assert r.json()["resultado"] in ("pendiente", "rechazado")
    assert db.rows("payments") == []
    assert db.rows("coupons")[0]["status"] == "Vigente"
    assert db.rows("studies")[0]["state"] == "Creado"
    assert len(db.rows("study_state_history")) == 1


def test_a_payment_with_another_amount_stores_nothing(client, db, mercadopago):
    mercadopago.add_payment("5551234", reference="genlab-study-4", amount="1.00")

    r = confirm(client, "5551234")

    assert r.status_code == 409
    assert r.json()["code"] == "monto_no_coincide"
    assert db.rows("payments") == []
    assert db.rows("studies")[0]["state"] == "Creado"


def test_the_charge_is_made_with_the_budget_stored_in_the_database(client, db, mercadopago):
    r = client.post(f"{PAY}/pago-mercadopago")

    assert r.status_code == 201, r.text
    assert (r.json()["importe_usd"], r.json()["importe"]) == (500, 1000.0)
    assert mercadopago.preferences[0]["external_reference"] == "genlab-study-4"
    assert db.rows("payments") == []
