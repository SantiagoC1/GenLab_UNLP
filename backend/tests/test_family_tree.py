from datetime import date, timedelta

import pytest

from app.core.enums import Rol
from app.integrations.familiograma import FamiliogramaInvalido, FamiliogramaSimulador
from app.modules.familiograma import service

PATIENT_ID = "123e4567-e89b-12d3-a456-426614174000"
KINSHIPS_URL = "/familiograma/kinships"
RELATIVES_URL = f"/familiograma/patients/{PATIENT_ID}/relatives"
TREE_URL = f"/familiograma/patients/{PATIENT_ID}/family-tree"
NOT_DOCTORS = [rol for rol in Rol if rol != Rol.MEDICO_TRATANTE]

PAIN = {"code": "SIM-001", "term": "Dolor"}
FABRY = {"id": 1, "name": "Fabry", "code": "FABRY", "cardinal": None, "secondary": []}


def valid_relative(**changes):
    relative = {
        "kinship_id": 1,
        "first_name": "Carolina",
        "last_name": "Ruiz",
        "sex": "mujer",
        "age": 36,
        "deceased": False,
        "symptoms": [PAIN],
        "pathology_ids": [1],
    }
    return {**relative, **changes}


class FakeModule(FamiliogramaSimulador):
    """El módulo de familiograma: guarda lo que recibe y puede fallar."""

    def __init__(self):
        self.received = []
        self.error = None

    def generar_familiograma(self, personas, regla_sospecha="desactivada"):
        self.received.append(personas)
        if self.error:
            raise self.error
        return {"advertencias": ["aviso"], "svg_base64": "PHN2Zz4="}


class World:
    """Reemplaza al repositorio, al catálogo y al módulo con datos en memoria."""

    def __init__(self):
        self.patient = {
            "id": PATIENT_ID,
            "first_name": "Tomás",
            "last_name": "Ruiz",
            "birth_date": (date.today() - timedelta(days=365 * 9 + 3)).isoformat(),
            "sex": "hombre",
            "patient_symptoms": [{"symptoms": PAIN}],
        }
        self.rows = []
        self.module = FakeModule()

    def find_patient(self, patient_id):
        return self.patient if patient_id == PATIENT_ID else None

    def list_by_patient(self, patient_id):
        return self.rows

    def replace_all(self, patient_id, rows):
        self.rows = [{"id": number, **row} for number, row in enumerate(rows, start=1)]


@pytest.fixture
def world(monkeypatch):
    fake = World()
    monkeypatch.setattr("app.modules.config_medica.repository.list_all", lambda: [FABRY])
    monkeypatch.setattr("app.modules.familiograma.repository.find_patient", fake.find_patient)
    monkeypatch.setattr("app.modules.familiograma.repository.list_by_patient", fake.list_by_patient)
    monkeypatch.setattr("app.modules.familiograma.repository.replace_all", fake.replace_all)
    monkeypatch.setattr(service, "obtener_familiograma", lambda: fake.module)
    return fake


def test_the_doctor_lists_the_kinships_without_the_patient(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.get(KINSHIPS_URL)

    assert response.status_code == 200
    assert {"id": 1, "name": "progenitor"} in response.json()
    assert all(item["id"] != 0 for item in response.json())


def test_listing_the_kinships_answers_503_if_the_module_fails(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.module.listar_parentescos = lambda: (_ for _ in ()).throw(ConnectionError())

    assert client.get(KINSHIPS_URL).status_code == 503


@pytest.mark.parametrize("role", NOT_DOCTORS)
@pytest.mark.parametrize("method", ["get", "put"])
def test_only_the_doctor_uses_the_relatives(client, login_as, world, role, method):
    login_as(role)

    response = getattr(client, method)(RELATIVES_URL)

    assert response.status_code == 403


@pytest.mark.parametrize("role", NOT_DOCTORS)
def test_only_the_doctor_asks_for_the_family_tree(client, login_as, world, role):
    login_as(role)

    assert client.get(TREE_URL).status_code == 403


def test_saving_replaces_the_relatives_and_returns_them(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.put(RELATIVES_URL, json={"relatives": [valid_relative()]})

    assert response.status_code == 200
    assert response.json() == [
        {
            "kinship_id": 1,
            "first_name": "Carolina",
            "last_name": "Ruiz",
            "sex": "mujer",
            "age": 36.0,
            "deceased": False,
            "symptoms": [PAIN],
            "pathologies": [{"id": 1, "code": "FABRY", "name": "Fabry"}],
        }
    ]
    assert client.get(RELATIVES_URL).json() == response.json()


def test_saving_an_empty_list_clears_the_relatives(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    client.put(RELATIVES_URL, json={"relatives": [valid_relative()]})

    response = client.put(RELATIVES_URL, json={"relatives": []})

    assert response.status_code == 200
    assert response.json() == []


def test_saving_reports_every_error_together_and_saves_nothing(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    body = {"relatives": [valid_relative(sex="otro"), valid_relative(first_name=None)]}

    response = client.put(RELATIVES_URL, json=body)

    assert response.status_code == 422
    assert "Familiar 1:" in response.json()["detalle"]
    assert "Familiar 2:" in response.json()["detalle"]
    assert world.rows == []


def test_an_unknown_patient_answers_404(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    other = "/familiograma/patients/otro-id"

    assert client.get(f"{other}/relatives").status_code == 404
    assert client.put(f"{other}/relatives", json={"relatives": []}).status_code == 404
    assert client.get(f"{other}/family-tree").status_code == 404


def test_the_family_tree_sends_the_patient_as_kinship_zero_with_the_relatives(
    client, login_as, world
):
    login_as(Rol.MEDICO_TRATANTE)
    client.put(RELATIVES_URL, json={"relatives": [valid_relative(deceased=True)]})

    response = client.get(TREE_URL)

    assert response.status_code == 200
    assert response.json() == {"warnings": ["aviso"], "svg_base64": "PHN2Zz4="}
    patient, relative = world.module.received[0]
    assert patient["parentesco"] == 0
    assert patient["nombre"] == "Tomás"
    assert patient["sexo"] == "hombre"
    assert patient["edad"] == 9.0
    assert patient["sintomas"] == [{"codigo": "SIM-001", "nombre": "Dolor"}]
    assert relative == {
        "parentesco": 1,
        "nombre": "Carolina",
        "apellido": "Ruiz",
        "sexo": "mujer",
        "edad": 36.0,
        "fallecido": True,
        "sintomas": [{"codigo": "SIM-001", "nombre": "Dolor"}],
        "diagnosticos": [{"codigo": "FABRY", "nombre": "Fabry"}],
    }


def test_a_patient_without_sex_goes_as_not_identified(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patient["sex"] = None

    client.get(TREE_URL)

    assert world.module.received[0][0]["sexo"] == "no_identificado"


def test_a_baby_goes_with_a_fractional_age(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patient["birth_date"] = (date.today() - timedelta(days=185)).isoformat()

    client.get(TREE_URL)

    assert 0 < world.module.received[0][0]["edad"] < 1


def test_the_family_tree_works_without_relatives(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    assert client.get(TREE_URL).status_code == 200
    assert len(world.module.received[0]) == 1


def test_the_family_tree_reports_what_the_module_rejected(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.module.error = FamiliogramaInvalido("Vínculos ambiguos", [])

    response = client.get(TREE_URL)

    assert response.status_code == 422
    assert "Vínculos ambiguos" in response.json()["detalle"]


def test_the_family_tree_answers_503_and_keeps_the_relatives_if_the_module_fails(
    client, login_as, world
):
    login_as(Rol.MEDICO_TRATANTE)
    client.put(RELATIVES_URL, json={"relatives": [valid_relative()]})
    world.module.error = ConnectionError()

    response = client.get(TREE_URL)

    assert response.status_code == 503
    assert len(client.get(RELATIVES_URL).json()) == 1
