"""Coupons and payment on the database repositories, after the coupons module restarted.

The coupons module (MA3, here its simulator) keeps what it issued in memory and forgets it when
the backend restarts, while the coupons are still in the `coupons` table. The flow has to keep
working: the platform tells the module which coupons it holds before asking about them.
No repository is overridden: the real wiring runs on the fake Supabase client.
"""

import pytest

from app.core.enums import Rol
from app.integrations import cupones as integracion_cupones
from app.integrations.avisos import obtener_avisos
from app.main import app
from tests.fake_supabase import FakeSupabase
from tests.fakes import AvisosEspia

ADMIN_ID = "u-admin"
PATIENT_ID = "9b1f6a52-0c1d-4e62-8f7a-2f0f4a5d9c11"
OTHER_PATIENT_ID = "3c7d1e90-5a2b-4f83-9d64-1b8e0a7c2f55"
PATIENT_MAIL = "paula.ramos@example.com"
DOCTOR_MAIL = "ana.perez@example.com"
PAY = "/presupuesto_pago/mis-estudios/4"


def coupon(code: str, status: str = "Vigente", pct: int = 20, doctor=None, patient=None) -> dict:
    return {
        "code": code,
        "discount_pct": pct,
        "status": status,
        "doctor_id": doctor,
        "patient_id": patient,
    }


@pytest.fixture
def db(monkeypatch):
    """Paula's study 4 has its 500 USD budget; the coupons are in the table already."""
    fake = FakeSupabase(
        users=[
            {"id": ADMIN_ID, "email": "admin@example.com", "role": Rol.ADMINISTRATIVO_LABORATORIO},
            {"id": "u-doctor", "email": DOCTOR_MAIL, "role": Rol.MEDICO_TRATANTE},
            {"id": "u-paula", "email": PATIENT_MAIL, "role": Rol.PACIENTE},
            {"id": "u-otro", "email": "otro@example.com", "role": Rol.PACIENTE},
        ],
        patients=[
            {
                "id": PATIENT_ID,
                "account_user_id": "u-paula",
                "first_name": "Paula",
                "last_name": "Ramos",
            },
            {
                "id": OTHER_PATIENT_ID,
                "account_user_id": "u-otro",
                "first_name": "Otro",
                "last_name": "Paciente",
            },
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
            coupon("CUP-0002", doctor="u-doctor", patient=PATIENT_ID),
            coupon("CUP-0003", doctor="u-doctor", patient=OTHER_PATIENT_ID),
            coupon("CUP-0004", status="Usado", doctor="u-doctor", patient=PATIENT_ID),
            coupon("CUP-0005", pct=10),
        ],
    )
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    monkeypatch.setattr("app.modules.consulta_medica.repository.supabase_admin", fake)
    # The backend was restarted: the coupons module remembers nothing.
    integracion_cupones.reiniciar_simulador()
    yield fake
    integracion_cupones.reiniciar_simulador()


@pytest.fixture
def avisos():
    espia = AvisosEspia()
    app.dependency_overrides[obtener_avisos] = lambda: espia
    return espia


def as_patient(login_as):
    login_as(Rol.PACIENTE, id="u-paula", email=PATIENT_MAIL)


def test_a_coupon_in_the_database_is_applied_and_paid_after_a_restart(client, login_as, db, avisos):
    as_patient(login_as)

    applied = client.post(f"{PAY}/cupon", json={"codigo": "CUP-0002"})
    assert applied.status_code == 200, applied.text
    assert applied.json()["descuento"] == 20
    assert applied.json()["importe_con_descuento_usd"] == 400
    (budget,) = db.rows("budgets")
    assert (budget["applied_coupon_code"], budget["applied_coupon_pct"]) == ("CUP-0002", 20)

    paid = client.post(f"{PAY}/pago", json={"metodo": "tarjeta_credito"})
    assert paid.status_code == 201, paid.text
    assert paid.json()["cupon"] == "CUP-0002"
    assert paid.json()["cupon_informado"] is True
    assert paid.json()["importe_usd"] == 400

    used = next(c for c in db.rows("coupons") if c["code"] == "CUP-0002")
    assert used["status"] == "Usado"
    (payment,) = db.rows("payments")
    assert payment["study_id"] == 4
    assert payment["amount_usd"] == 400
    assert payment["method"] == "tarjeta_credito"
    assert payment["coupon_code"] == "CUP-0002"
    assert payment["coupon_id"] == used["id"]
    assert db.rows("studies")[0]["state"] == "Pagado"
    last = db.rows("study_state_history")[-1]
    assert (last["from_state"], last["to_state"], last["changed_by"]) == (
        "Creado",
        "Pagado",
        "u-paula",
    )


def test_a_coupon_already_used_is_rejected_with_its_real_state(client, login_as, db, avisos):
    as_patient(login_as)

    r = client.post(f"{PAY}/cupon", json={"codigo": "CUP-0004"})

    assert r.status_code == 409
    assert r.json()["code"] == "cupon_no_vigente"
    assert "Usado" in r.json()["detalle"]


def test_the_coupon_of_another_patient_is_still_rejected(client, login_as, db, avisos):
    as_patient(login_as)

    r = client.post(f"{PAY}/cupon", json={"codigo": "CUP-0003"})

    assert r.status_code == 409
    assert r.json()["code"] == "cupon_de_otro_paciente"
    assert db.rows("budgets")[0]["applied_coupon_code"] is None


def test_a_code_that_exists_nowhere_is_still_inexistente(client, login_as, db, avisos):
    as_patient(login_as)

    r = client.post(f"{PAY}/cupon", json={"codigo": "CUP-9999"})

    assert r.status_code == 409
    assert "Inexistente" in r.json()["detalle"]


def test_the_manager_can_assign_a_stored_coupon_to_a_doctor_after_a_restart(
    client, login_as, db, avisos
):
    login_as(Rol.GERENTE_MEDICO, id="u-gerente", email="gerente@example.com")

    r = client.post(
        "/cupones/asignar-a-medico", json={"contacto_medico": DOCTOR_MAIL, "codigos": ["CUP-0005"]}
    )

    assert r.status_code == 200, r.text
    assigned = next(c for c in db.rows("coupons") if c["code"] == "CUP-0005")
    assert assigned["doctor_id"] == "u-doctor"


def test_new_coupons_continue_the_numbering_of_the_stored_ones(client, login_as, db, avisos):
    login_as(Rol.GERENTE_MEDICO, id="u-gerente", email="gerente@example.com")

    r = client.post("/cupones/generar", json={"descuento": 15, "cantidad": 2})

    assert r.status_code == 201, r.text
    assert [c["codigo"] for c in r.json()] == ["CUP-0006", "CUP-0007"]
    codes = [c["code"] for c in db.rows("coupons")]
    assert len(codes) == len(set(codes)) == 6
