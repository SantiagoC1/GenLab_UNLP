"""The budget tray, end to end through the real wiring (no repository is overridden).

Without DEV_AUTH the studies come from the database: one created by the doctor shows up in the
tray, and leaves it once the budget is issued. With DEV_AUTH the tray shows the in-memory demo
studies and never the database ones.
"""

import pytest

from app.core.enums import Rol
from app.integrations.avisos import obtener_avisos
from app.main import app
from tests.fake_supabase import FakeSupabase
from tests.fakes import AvisosEspia

ADMIN_ID = "u-admin"
PATIENT_MAIL = "paula.ramos@example.com"
GENES = ["GBA", "GLA", "IDUA"]
TRAY = "/presupuesto_pago/estudios-pendientes"


@pytest.fixture
def db(monkeypatch):
    """A database with one study created by the doctor, the way module 3 leaves it."""
    fake = FakeSupabase(
        users=[
            {"id": ADMIN_ID, "email": "admin@example.com", "role": Rol.ADMINISTRATIVO_LABORATORIO},
            {"id": "u-doctor", "email": "ana.perez@example.com", "role": Rol.MEDICO_TRATANTE},
            {"id": "u-paula", "email": PATIENT_MAIL, "role": Rol.PACIENTE},
        ],
        patients=[
            {
                "id": "9b1f6a52-0c1d-4e62-8f7a-2f0f4a5d9c11",
                "account_user_id": "u-paula",
                "first_name": "Paula",
                "last_name": "Ramos",
            }
        ],
        studies=[
            {
                "id": 4,
                "patient_id": "9b1f6a52-0c1d-4e62-8f7a-2f0f4a5d9c11",
                "requested_by": "u-doctor",
                "state": "Creado",
            }
        ],
        study_genes=[{"study_id": 4, "gene": gene} for gene in GENES],
        study_state_history=[
            {"study_id": 4, "from_state": None, "to_state": "Creado", "changed_by": "u-doctor"}
        ],
    )
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    monkeypatch.setattr("app.modules.consulta_medica.repository.supabase_admin", fake)
    return fake


@pytest.fixture
def avisos():
    espia = AvisosEspia()
    app.dependency_overrides[obtener_avisos] = lambda: espia
    return espia


def names(client) -> list[str]:
    response = client.get(TRAY)
    assert response.status_code == 200, response.text
    return [row["paciente"] for row in response.json()]


def test_a_study_created_in_the_database_shows_up_and_leaves_after_issuing_the_budget(
    client, login_as, monkeypatch, db, avisos
):
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO, id=ADMIN_ID)

    # Only the database study: none of the in-memory demo studies leaks into the tray.
    bandeja = client.get(TRAY).json()
    assert bandeja == [{"id": 4, "paciente": "Paula Ramos", "cantidad_genes": len(GENES)}]

    emitido = client.post("/presupuesto_pago/estudios/4/presupuesto")
    assert emitido.status_code == 201, emitido.text
    assert emitido.json()["paciente_avisado"] is True
    assert avisos.para(PATIENT_MAIL)

    # The budget is a row of `budgets` made by the administrative user, and the tray is empty.
    (presupuesto,) = db.rows("budgets")
    assert presupuesto["study_id"] == 4
    assert presupuesto["issued_by"] == ADMIN_ID
    assert presupuesto["gene_count"] == len(GENES)
    assert names(client) == []


def test_the_detail_and_a_second_budget_also_go_through_the_database(
    client, login_as, monkeypatch, db, avisos
):
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO, id=ADMIN_ID)

    detalle = client.get("/presupuesto_pago/estudios/4")
    assert detalle.status_code == 200
    assert detalle.json()["paciente"] == "Paula Ramos"
    assert detalle.json()["genes"] == sorted(GENES)

    client.post("/presupuesto_pago/estudios/4/presupuesto")
    again = client.post("/presupuesto_pago/estudios/4/presupuesto")
    assert again.status_code == 409
    assert len(db.rows("budgets")) == 1


def test_with_dev_auth_the_tray_shows_the_demo_data_and_not_the_database(
    client, login_as, monkeypatch, db
):
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: True)
    login_as(Rol.ADMINISTRATIVO_LABORATORIO, id=ADMIN_ID)

    assert "Paula Ramos" not in names(client)
    assert db.rows("budgets") == []
