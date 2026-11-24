import pytest

from app.core.enums import Rol

DOCTOR_URL = "/consulta_medica/studies"
PATIENT_URL = "/consulta_medica/my-studies"

ROW = {
    "id": 7,
    "state": "Creado",
    "pompe_urgent": True,
    "created_at": "2026-11-20T10:00:00+00:00",
    "state_changed_at": "2026-11-20T10:00:00+00:00",
    "patients": {
        "first_name": "Lucía",
        "last_name": "Fernández",
        "dni": "30123456",
        "account_user_id": "u-sesion",
    },
    "study_pathologies": [{"pathologies": {"name": "Pompe"}}, {"pathologies": {"name": "Fabry"}}],
    "study_genes": [{"count": 3}],
}


@pytest.fixture
def asked(monkeypatch):
    """Reemplaza las dos consultas de Supabase y guarda con qué id se pidieron."""
    calls = {}

    def by_doctor(doctor_id):
        calls["doctor"] = doctor_id
        return [ROW]

    def by_account(account_id):
        calls["account"] = account_id
        return [ROW]

    monkeypatch.setattr(
        "app.modules.consulta_medica.repository.list_studies_requested_by", by_doctor
    )
    monkeypatch.setattr(
        "app.modules.consulta_medica.repository.list_studies_of_account", by_account
    )
    return calls


def test_the_doctor_sees_the_studies_he_requested(client, login_as, asked):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.get(DOCTOR_URL)

    assert response.status_code == 200
    assert asked == {"doctor": "u-sesion"}
    assert response.json() == [
        {
            "id": 7,
            "state": "Creado",
            "pompe_urgent": True,
            "created_at": ROW["created_at"],
            "state_changed_at": ROW["state_changed_at"],
            "patient_name": "Lucía Fernández",
            "patient_dni": "30123456",
            "pathologies": ["Pompe", "Fabry"],
            "gene_count": 3,
        }
    ]


def test_the_patient_sees_the_studies_of_his_account(client, login_as, asked):
    login_as(Rol.PACIENTE)

    response = client.get(PATIENT_URL)

    assert response.status_code == 200
    assert asked == {"account": "u-sesion"}
    assert response.json()[0]["id"] == 7


@pytest.mark.parametrize("rol", [rol for rol in Rol if rol != Rol.MEDICO_TRATANTE])
def test_only_the_doctor_lists_requested_studies(client, login_as, asked, rol):
    login_as(rol)

    assert client.get(DOCTOR_URL).status_code == 403


@pytest.mark.parametrize("rol", [rol for rol in Rol if rol != Rol.PACIENTE])
def test_only_the_patient_lists_his_studies(client, login_as, asked, rol):
    login_as(rol)

    assert client.get(PATIENT_URL).status_code == 403
