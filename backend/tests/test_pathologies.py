import pytest

from app.core.enums import Rol
from app.models import pathology as pathology_model

LIST_URL = "/config_medica/pathologies"
READERS = [Rol.GERENTE_MEDICO, Rol.MEDICO_TRATANTE]
NOT_READERS = [rol for rol in Rol if rol not in READERS]
NOT_MANAGERS = [rol for rol in Rol if rol != Rol.GERENTE_MEDICO]

PAIN = {"code": "SIM-001", "term": "Dolor"}
FEVER = {"code": "SIM-002", "term": "Fiebre"}
TIREDNESS = {"code": "SIM-003", "term": "Cansancio"}
RASH = {"code": "SIM-004", "term": "Erupción"}


def valid_payload(**changes):
    payload = {"name": "Fabry", "cardinal": PAIN, "secondary": [FEVER, TIREDNESS]}
    return {**payload, **changes}


class FakeCatalog:
    """Reemplaza al modelo: guarda las patologías en memoria y registra lo que recibe."""

    def __init__(self, pathologies=None):
        self.pathologies = list(pathologies or [])
        self.created = []
        self.replaced = []
        self.fail_with = None

    def list_all(self):
        return self.pathologies

    def find_by_id(self, pathology_id):
        return next((p for p in self.pathologies if p["id"] == pathology_id), None)

    def name_exists(self, name):
        key = pathology_model.name_key(name)
        return any(pathology_model.name_key(p["name"]) == key for p in self.pathologies)

    def create(self, name, cardinal, secondary):
        if self.fail_with:
            raise self.fail_with
        self.created.append((name, cardinal, secondary))
        pathology = {"id": 99, "name": name, "cardinal": cardinal, "secondary": secondary}
        self.pathologies.append(pathology)
        return pathology

    def replace_symptoms(self, pathology_id, cardinal, secondary):
        self.replaced.append((pathology_id, cardinal, secondary))
        pathology = self.find_by_id(pathology_id)
        pathology.update(cardinal=cardinal, secondary=secondary)
        return pathology


@pytest.fixture
def catalog(monkeypatch):
    """Parcha el modelo donde lo usan el servicio y las validaciones. Uso: `catalog(pathologies)`."""

    def _install(pathologies=None):
        fake = FakeCatalog(pathologies)
        for name in ("list_all", "find_by_id", "name_exists", "create", "replace_symptoms"):
            monkeypatch.setattr(f"app.models.pathology.{name}", getattr(fake, name))
        return fake

    return _install


def stored(pathology_id=1, name="Pompe"):
    return {
        "id": pathology_id,
        "name": name,
        "cardinal": PAIN,
        "secondary": [FEVER, TIREDNESS],
    }


@pytest.mark.parametrize("role", READERS)
def test_the_catalog_can_be_read_by_the_manager_and_the_treating_doctor(
    client, login_as, catalog, role
):
    login_as(role)
    catalog([stored()])

    response = client.get(LIST_URL)

    assert response.status_code == 200
    assert response.json() == [stored()]


@pytest.mark.parametrize("role", NOT_READERS)
def test_the_catalog_cannot_be_read_by_other_roles(client, login_as, catalog, role):
    login_as(role)
    catalog()

    assert client.get(LIST_URL).status_code == 403


def test_the_catalog_requires_a_session(client, catalog):
    catalog()

    assert client.get(LIST_URL).status_code == 401


def test_the_manager_creates_a_pathology(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()

    response = client.post(LIST_URL, json=valid_payload())

    assert response.status_code == 201
    assert response.json()["name"] == "Fabry"
    assert fake.created == [("Fabry", PAIN, [FEVER, TIREDNESS])]


def test_creating_trims_the_name_and_the_symptoms(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()
    payload = valid_payload(
        name="  Fabry  ",
        cardinal={"code": " SIM-001 ", "term": " Dolor "},
    )

    assert client.post(LIST_URL, json=payload).status_code == 201

    assert fake.created[0][:2] == ("Fabry", PAIN)


@pytest.mark.parametrize("role", NOT_MANAGERS)
def test_only_the_manager_can_create(client, login_as, catalog, role):
    login_as(role)
    fake = catalog()

    response = client.post(LIST_URL, json=valid_payload())

    assert response.status_code == 403
    assert fake.created == []


def test_creating_requires_a_session(client, catalog):
    catalog()

    assert client.post(LIST_URL, json=valid_payload()).status_code == 401


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (valid_payload(name=None), "nombre de la patología"),
        (valid_payload(name="   "), "nombre de la patología"),
        (valid_payload(name="x" * 101), "más de 100 caracteres"),
        (valid_payload(name="Fa\x00bry"), "caracteres de control"),
        (valid_payload(name="Fa\tbry"), "caracteres de control"),
        (valid_payload(secondary=[FEVER, {**FEVER, "code": " sim-002 "}]), "no pueden repetirse"),
        (valid_payload(secondary=[{**PAIN, "code": "sim-001"}, FEVER]), "no puede repetirse"),
        (valid_payload(cardinal=None), "síntoma cardinal"),
        (valid_payload(cardinal={"code": "", "term": "Dolor"}), "cardinal no es válido"),
        (valid_payload(cardinal={"code": "SIM-001"}), "cardinal no es válido"),
        (valid_payload(secondary=None), "al menos 2 síntomas secundarios"),
        (valid_payload(secondary=[FEVER]), "al menos 2 síntomas secundarios"),
        (
            valid_payload(secondary=[FEVER, {"code": "x", "term": ""}]),
            "secundario que no es válido",
        ),
        (valid_payload(secondary=[FEVER, FEVER]), "no pueden repetirse"),
        (valid_payload(secondary=[PAIN, FEVER]), "no puede repetirse como secundario"),
        (
            valid_payload(secondary=[{"code": f"S-{n}", "term": "t"} for n in range(31)]),
            "más de 30 síntomas secundarios",
        ),
        (
            valid_payload(cardinal={"code": "SIM-001", "term": "Do\x00lor"}),
            "cardinal no es válido",
        ),
    ],
)
def test_creating_rejects_invalid_data(client, login_as, catalog, payload, message):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()

    response = client.post(LIST_URL, json=payload)

    assert response.status_code == 422
    assert message in response.json()["detalle"]
    assert fake.created == []


def test_creating_reports_all_the_errors_together(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    catalog()

    response = client.post(LIST_URL, json={})

    detail = response.json()["detalle"]
    assert response.status_code == 422
    assert "nombre" in detail
    assert "cardinal" in detail
    assert "secundarios" in detail


@pytest.mark.parametrize(
    ("payload", "stored_name"),
    [
        (valid_payload(name="x" * 100), "x" * 100),
        (valid_payload(name="  Fabry   clásico "), "Fabry clásico"),
        (valid_payload(secondary=[{"code": f"S-{n}", "term": "t"} for n in range(30)]), "Fabry"),
        (valid_payload(secondary=[FEVER, TIREDNESS]), "Fabry"),
    ],
)
def test_creating_accepts_the_limits_and_normalizes_the_name(
    client, login_as, catalog, payload, stored_name
):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()

    response = client.post(LIST_URL, json=payload)

    assert response.status_code == 201
    assert fake.created[0][0] == stored_name


@pytest.mark.parametrize(
    "name",
    [
        "POMPE ",  # espacio no cortante al final
        "ＰＯＭＰＥ",  # letras de ancho completo
    ],
)
def test_creating_does_not_duplicate_equivalent_names(client, login_as, catalog, name):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog([stored(name="Pompe")])

    response = client.post(LIST_URL, json=valid_payload(name=name))

    assert response.status_code == 422
    assert "Ya existe una patología con ese nombre" in response.json()["detalle"]
    assert fake.created == []


@pytest.mark.parametrize("name", ["Pompe", "pompe", "  POMPE "])
def test_creating_does_not_duplicate_a_pathology(client, login_as, catalog, name):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog([stored(name="Pompe")])

    response = client.post(LIST_URL, json=valid_payload(name=name))

    assert response.status_code == 422
    assert "Ya existe una patología con ese nombre" in response.json()["detalle"]
    assert fake.created == []


def test_a_name_taken_in_between_answers_409(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()
    fake.fail_with = pathology_model.NameTaken()

    response = client.post(LIST_URL, json=valid_payload())

    assert response.status_code == 409
    assert "Ya existe una patología" in response.json()["detalle"]


def test_a_failure_while_saving_is_not_hidden(login_as, catalog):
    from fastapi.testclient import TestClient

    from app.main import app

    login_as(Rol.GERENTE_MEDICO)
    fake = catalog()
    fake.fail_with = RuntimeError("falló la base")

    response = TestClient(app, raise_server_exceptions=False).post(LIST_URL, json=valid_payload())

    assert response.status_code == 500


def test_the_manager_replaces_the_symptoms(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog([stored()])
    payload = {"cardinal": RASH, "secondary": [PAIN, FEVER]}

    response = client.put(f"{LIST_URL}/1/symptoms", json=payload)

    assert response.status_code == 200
    assert response.json()["cardinal"] == RASH
    assert fake.replaced == [(1, RASH, [PAIN, FEVER])]


@pytest.mark.parametrize("role", NOT_MANAGERS)
def test_only_the_manager_can_replace_symptoms(client, login_as, catalog, role):
    login_as(role)
    fake = catalog([stored()])

    response = client.put(
        f"{LIST_URL}/1/symptoms", json={"cardinal": RASH, "secondary": [PAIN, FEVER]}
    )

    assert response.status_code == 403
    assert fake.replaced == []


def test_replacing_symptoms_of_an_unknown_pathology_answers_404(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    catalog([stored()])

    response = client.put(
        f"{LIST_URL}/7/symptoms", json={"cardinal": RASH, "secondary": [PAIN, FEVER]}
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"cardinal": None, "secondary": [PAIN, FEVER]},
        {"cardinal": RASH, "secondary": [PAIN]},
        {"cardinal": RASH, "secondary": [RASH, PAIN]},
        {"cardinal": RASH, "secondary": [PAIN, PAIN]},
    ],
)
def test_replacing_rejects_invalid_symptoms(client, login_as, catalog, payload):
    login_as(Rol.GERENTE_MEDICO)
    fake = catalog([stored()])

    response = client.put(f"{LIST_URL}/1/symptoms", json=payload)

    assert response.status_code == 422
    assert fake.replaced == []


def test_the_id_must_be_a_number(client, login_as, catalog):
    login_as(Rol.GERENTE_MEDICO)
    catalog()

    response = client.put(
        f"{LIST_URL}/abc/symptoms", json={"cardinal": RASH, "secondary": [PAIN, FEVER]}
    )

    assert response.status_code == 422
