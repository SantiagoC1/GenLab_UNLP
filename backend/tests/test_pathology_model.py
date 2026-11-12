from types import SimpleNamespace

import pytest
from postgrest.exceptions import APIError

from app.models import pathology as pathology_model

PAIN = {"code": "SIM-001", "term": "Dolor"}
FEVER = {"code": "SIM-002", "term": "Fiebre"}
TIREDNESS = {"code": "SIM-003", "term": "Cansancio"}
PATIENT_TABLES = {"patients", "patient_symptoms", "patient_pathologies"}


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.operations = []

    def __getattr__(self, operation):
        def record(*args, **kwargs):
            self.operations.append((operation, args, kwargs))
            return self

        return record

    def execute(self):
        operation = self.operations[0][0]
        self.client.calls.append((self.table, operation, self.operations[0][1]))
        failure = self.client.failures.get((self.table, operation))
        if failure:
            raise failure
        return SimpleNamespace(data=self.client.responses.get((self.table, operation), []))


class FakeClient:
    """Reemplaza al cliente de Supabase: registra cada tabla y operación, y falla si se le indica."""

    def __init__(self, responses=None, failures=None):
        self.responses = responses or {}
        self.failures = failures or {}
        self.calls = []

    def table(self, name):
        return FakeQuery(self, name)

    def operations(self):
        return [(table, operation) for table, operation, _ in self.calls]


@pytest.fixture
def client_with(monkeypatch):
    def _install(**kwargs):
        fake = FakeClient(**kwargs)
        monkeypatch.setattr(pathology_model, "supabase_admin", fake)
        return fake

    return _install


STORED_ROW = {
    "id": 7,
    "name": "Fabry",
    "pathology_symptoms": [
        {"is_cardinal": False, "symptoms": TIREDNESS},
        {"is_cardinal": True, "symptoms": PAIN},
        {"is_cardinal": False, "symptoms": FEVER},
    ],
}


def test_a_row_is_read_with_the_cardinal_apart_and_the_secondary_ordered(client_with):
    client_with(responses={("pathologies", "select"): [STORED_ROW]})

    result = pathology_model.list_all()

    assert result == [{"id": 7, "name": "Fabry", "cardinal": PAIN, "secondary": [TIREDNESS, FEVER]}]


def test_name_exists_ignores_case_and_spaces(client_with):
    client_with(responses={("pathologies", "select"): [{"name": "Pompe"}]})

    assert pathology_model.name_exists("  pOMPE ") is True
    assert pathology_model.name_exists("Fabry") is False


@pytest.mark.parametrize(
    ("stored", "typed"),
    [
        ("Niemann-Pick", "NIEMANN-PICK"),
        ("Fabry clásico", "Fabry  clásico"),  # espacios internos de más
        ("Fabry clásico", "Fabry clásico"),  # la tilde escrita en dos piezas
        ("Straße", "STRASSE"),  # ß y ss: casefold las iguala, lower() no
        ("Fabry", "Ｆａｂｒｙ"),  # letras de ancho completo
        ("Fabry X", "Fabry X"),  # espacio no cortante
    ],
)
def test_name_exists_treats_equivalent_unicode_forms_as_the_same(client_with, stored, typed):
    client_with(responses={("pathologies", "select"): [{"name": stored}]})

    assert pathology_model.name_exists(typed) is True


def test_names_are_stored_in_nfc_with_single_spaces():
    assert pathology_model.normalize_name("  Fabry   clásico ") == "Fabry clásico"


def test_creating_saves_the_symptoms_then_the_pathology_then_the_links(client_with):
    fake = client_with(
        responses={
            ("pathologies", "insert"): [{"id": 7}],
            ("pathologies", "select"): [STORED_ROW],
        }
    )

    pathology_model.create("Fabry", PAIN, [FEVER, TIREDNESS])

    assert fake.operations()[:3] == [
        ("symptoms", "upsert"),
        ("pathologies", "insert"),
        ("pathology_symptoms", "insert"),
    ]


def test_creating_with_a_taken_name_raises_name_taken(client_with):
    taken = APIError({"message": "duplicate", "code": "23505", "details": "", "hint": ""})
    client_with(failures={("pathologies", "insert"): taken})

    with pytest.raises(pathology_model.NameTaken):
        pathology_model.create("Fabry", PAIN, [FEVER, TIREDNESS])


def test_creating_deletes_the_half_made_pathology_when_the_links_fail(client_with):
    fake = client_with(
        responses={("pathologies", "insert"): [{"id": 7}]},
        failures={("pathology_symptoms", "insert"): RuntimeError("falló")},
    )

    with pytest.raises(RuntimeError):
        pathology_model.create("Fabry", PAIN, [FEVER, TIREDNESS])

    assert fake.operations()[-1] == ("pathologies", "delete")


def test_replacing_never_touches_the_patients_data(client_with):
    fake = client_with(
        responses={
            ("pathology_symptoms", "select"): [],
            ("pathologies", "select"): [STORED_ROW],
        }
    )

    pathology_model.replace_symptoms(7, PAIN, [FEVER, TIREDNESS])

    touched = {table for table, _ in fake.operations()}
    assert touched <= {"pathologies", "symptoms", "pathology_symptoms"}
    assert not touched & PATIENT_TABLES


def test_replacing_restores_the_previous_links_when_the_new_ones_fail(monkeypatch, client_with):
    previous = [{"pathology_id": 7, "symptom_code": "SIM-009", "is_cardinal": True}]
    client_with(responses={("pathology_symptoms", "select"): previous})
    inserts = []
    original = FakeQuery.execute

    def failing_first_insert(self):
        if self.table == "pathology_symptoms" and self.operations[0][0] == "insert":
            inserts.append(self.operations[0][1][0])
            if len(inserts) == 1:
                raise RuntimeError("falló")
        return original(self)

    monkeypatch.setattr(FakeQuery, "execute", failing_first_insert)

    with pytest.raises(RuntimeError):
        pathology_model.replace_symptoms(7, PAIN, [FEVER, TIREDNESS])

    assert inserts[1] == previous
