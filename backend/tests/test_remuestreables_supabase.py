"""Asking for a resampling, end to end on the database repositories (the fake Supabase client).

No repository is overridden, except the appointments (not persisted yet): the studies, the
resamplings and the history of the states go through the real wiring.
"""

import pytest

from app.core.enums import Rol
from app.integrations.avisos import obtener_avisos
from app.main import app
from app.modules.turnos import remuestreos as modulo_remuestreos
from app.modules.turnos.repositorio import RepositorioTurnosEnMemoria
from app.modules.turnos.repositorio import obtener_repositorio as obtener_repositorio_turnos
from tests.fake_supabase import FakeSupabase
from tests.fakes import AvisosEspia

ADMIN_ID = "u-admin"
PAULA_MAIL = "paula.ramos@example.com"
DOCTOR_MAIL = "ana.perez@example.com"
PAULA = "9b1f6a52-0c1d-4e62-8f7a-2f0f4a5d9c11"
OTRO = "3c7d1e90-5a2b-4f83-9d64-1b8e0a7c2f55"
LIST = "/turnos/estudios/remuestreables"
REASON = "mala_calidad_de_muestra"


def study(study_id: int, patient_id: str, state: str) -> dict:
    return {"id": study_id, "patient_id": patient_id, "requested_by": "u-doctor", "state": state}


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase(
        users=[
            {"id": ADMIN_ID, "email": "admin@example.com", "role": Rol.ADMINISTRATIVO_LABORATORIO},
            {"id": "u-doctor", "email": DOCTOR_MAIL, "role": Rol.MEDICO_TRATANTE},
            {"id": "u-paula", "email": PAULA_MAIL, "role": Rol.PACIENTE},
            {"id": "u-otro", "email": "otro@example.com", "role": Rol.PACIENTE},
        ],
        patients=[
            {
                "id": PAULA,
                "account_user_id": "u-paula",
                "first_name": "Paula",
                "last_name": "Ramos",
                "dni": "22321414",
            },
            {
                "id": OTRO,
                "account_user_id": "u-otro",
                "first_name": "Otro",
                "last_name": "Paciente",
                "dni": "30999888",
            },
        ],
        studies=[
            study(4, PAULA, "EnViajeACorea"),
            study(5, OTRO, "EnElAreaDeBioinformatica"),
            study(6, PAULA, "Creado"),
            study(7, OTRO, "EnLaboratorioCentral"),
        ],
        study_state_history=[
            {"study_id": 4, "from_state": None, "to_state": "EnViajeACorea", "changed_by": None},
            {"study_id": 5, "from_state": None, "to_state": "EnElAreaDeBioinformatica"},
        ],
        resamplings=[],
    )
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    monkeypatch.setattr("app.modules.consulta_medica.repository.supabase_admin", fake)
    monkeypatch.setattr("app.database.supabase_admin", fake)
    # The repository of the resamplings is created once: every test needs one on its own client.
    monkeypatch.setattr(modulo_remuestreos, "_supabase", None)
    app.dependency_overrides.pop(modulo_remuestreos.obtener_repositorio, None)
    app.dependency_overrides[obtener_repositorio_turnos] = lambda: RepositorioTurnosEnMemoria()
    return fake


@pytest.fixture
def avisos():
    espia = AvisosEspia()
    app.dependency_overrides[obtener_avisos] = lambda: espia
    return espia


def as_admin(login_as):
    login_as(Rol.ADMINISTRATIVO_LABORATORIO, id=ADMIN_ID)


def ask(client, study_id=4, detail="La muestra llegó hemolizada.", reason=REASON):
    return client.post(
        f"/turnos/estudios/{study_id}/remuestreo-administrativo",
        json={"motivo": reason, "detalle": detail},
    )


def test_the_list_has_only_the_studies_in_korea_or_in_bioinformatics_with_the_dni(
    client, login_as, db, avisos
):
    as_admin(login_as)

    r = client.get(LIST)

    assert r.status_code == 200, r.text
    assert r.json() == [
        {
            "estudio_id": 4,
            "paciente": "Paula Ramos",
            "dni": "22321414",
            "estado": "EnViajeACorea",
            "remuestreo_pendiente": None,
        },
        {
            "estudio_id": 5,
            "paciente": "Otro Paciente",
            "dni": "30999888",
            "estado": "EnElAreaDeBioinformatica",
            "remuestreo_pendiente": None,
        },
    ]


def test_asking_stores_the_resampling_and_the_study_goes_back_to_turno_sacado(
    client, login_as, db, avisos
):
    as_admin(login_as)

    r = ask(client)

    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "TurnoSacado"
    assert r.json()["medico_avisado"] and r.json()["paciente_avisado"]
    (row,) = db.rows("resamplings")
    assert (row["study_id"], row["reason"], row["detail"], row["requested_by"]) == (
        4,
        REASON,
        "La muestra llegó hemolizada.",
        ADMIN_ID,
    )
    assert row["resolved_at"] is None
    assert next(s for s in db.rows("studies") if s["id"] == 4)["state"] == "TurnoSacado"
    last = db.rows("study_state_history")[-1]
    assert (last["study_id"], last["from_state"], last["to_state"]) == (
        4,
        "EnViajeACorea",
        "TurnoSacado",
    )
    assert avisos.para(PAULA_MAIL) and avisos.para(DOCTOR_MAIL)


def test_once_asked_the_study_leaves_the_list_and_cannot_be_asked_again(
    client, login_as, db, avisos
):
    as_admin(login_as)
    ask(client)

    assert [e["estudio_id"] for e in client.get(LIST).json()] == [5]
    again = ask(client)
    assert again.status_code == 409
    assert again.json()["code"] == "estudio_sin_remuestreo_posible"
    assert len(db.rows("resamplings")) == 1


def test_a_pending_resampling_is_listed_and_blocks_a_new_request(client, login_as, db, avisos):
    as_admin(login_as)
    db.rows("resamplings").append(
        db.complete(
            "resamplings",
            {"study_id": 4, "reason": "adn_desnaturalizado", "detail": "Pedido anterior"},
        )
    )

    pending = client.get(LIST).json()[0]["remuestreo_pendiente"]
    assert (pending["motivo"], pending["detalle"]) == ("adn_desnaturalizado", "Pedido anterior")

    r = ask(client)
    assert r.status_code == 409
    assert r.json()["code"] == "remuestreo_pendiente"
    assert len(db.rows("resamplings")) == 1
    assert next(s for s in db.rows("studies") if s["id"] == 4)["state"] == "EnViajeACorea"


def test_a_study_in_another_state_is_refused(client, login_as, db, avisos):
    as_admin(login_as)

    for study_id in (6, 7):
        r = ask(client, study_id)
        assert r.status_code == 409
        assert r.json()["code"] == "estudio_sin_remuestreo_posible"
    assert ask(client, 99).status_code == 404
    assert db.rows("resamplings") == []


def test_the_patient_sees_the_new_booking_enabled_with_the_reason(client, login_as, db, avisos):
    as_admin(login_as)
    ask(client, reason="adn_desnaturalizado", detail="ADN degradado.")

    login_as(Rol.PACIENTE, id="u-paula", email=PAULA_MAIL)
    habilitados = client.get("/turnos/habilitados").json()

    assert [(h["estudio_id"], h["estado"], h["remuestreo_motivo"]) for h in habilitados] == [
        (4, "TurnoSacado", "adn_desnaturalizado")
    ]


def test_only_the_administrative_user_asks_and_lists(client, login_as, db, avisos):
    for rol in (Rol.PACIENTE, Rol.BIOINFORMATICO, Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO):
        login_as(rol, id="u-x", email="x@example.com")
        assert client.get(LIST).status_code == 403
        assert ask(client).status_code == 403
    assert db.rows("resamplings") == []
