import pytest

from app.modules.familiograma import repository
from app.modules.familiograma.validate import (
    MAX_RELATIVES,
    MAX_SYMPTOMS,
    validate_relatives,
)

PAIN = {"code": "SIM-001", "term": "Dolor"}


@pytest.fixture(autouse=True)
def catalog(monkeypatch):
    monkeypatch.setattr(
        "app.modules.familiograma.validate.pathology_repository.list_all",
        lambda: [{"id": 1}, {"id": 2}],
    )


def relative(**changes):
    data = {
        "kinship_id": 1,
        "first_name": "Carolina",
        "last_name": "Ruiz",
        "sex": "mujer",
        "age": 36,
        "deceased": False,
        "symptoms": [PAIN],
        "pathology_ids": [1],
    }
    return {**data, **changes}


def test_a_complete_relative_is_valid():
    assert validate_relatives({"relatives": [relative()]}) == []


def test_an_empty_list_is_valid_and_clears_the_relatives():
    assert validate_relatives({"relatives": []}) == []


def test_the_list_is_required():
    assert validate_relatives({}) == ["Mandá la lista de familiares."]


def test_the_age_and_the_diagnoses_can_be_missing():
    errors = validate_relatives(
        {"relatives": [relative(age=None, pathology_ids=None, symptoms=None)]}
    )

    assert errors == []


@pytest.mark.parametrize("field", ["kinship_id", "first_name", "last_name", "sex"])
def test_every_required_field_is_checked(field):
    errors = validate_relatives({"relatives": [relative(**{field: None})]})

    assert len(errors) == 1
    assert "es obligatorio" in errors[0]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"kinship_id": 0}, "no puede ser el del paciente"),
        ({"first_name": "  "}, "es obligatorio"),
        ({"first_name": "A" * 101}, "no puede tener más de 100"),
        ({"last_name": "Ru\niz"}, "caracteres que no se pueden usar"),
        ({"sex": "otro"}, "hombre, mujer o no identificado"),
        ({"age": -1}, "entre 0 y 120"),
        ({"age": 121}, "entre 0 y 120"),
        ({"symptoms": [{"code": "SIM-001"}]}, "síntoma que no es válido"),
        ({"symptoms": [PAIN, PAIN]}, "no pueden repetirse"),
        ({"pathology_ids": [1, 1]}, "no pueden repetirse"),
        ({"pathology_ids": [99]}, "no está en el catálogo"),
    ],
)
def test_the_formats_are_checked(changes, message):
    errors = validate_relatives({"relatives": [relative(**changes)]})

    assert len(errors) == 1
    assert message in errors[0]


def test_a_fractional_age_is_valid():
    assert validate_relatives({"relatives": [relative(age=0.5)]}) == []


def test_the_errors_say_which_relative_they_belong_to():
    errors = validate_relatives({"relatives": [relative(), relative(sex="otro")]})

    assert errors[0].startswith("Familiar 2: ")


def test_the_errors_of_all_the_relatives_come_together():
    errors = validate_relatives(
        {"relatives": [relative(first_name=None), relative(last_name=None)]}
    )

    assert len(errors) == 2


def test_the_number_of_relatives_is_limited():
    data = {"relatives": [relative() for _ in range(MAX_RELATIVES + 1)]}

    assert "más de 30 familiares" in validate_relatives(data)[0]


def test_the_number_of_symptoms_is_limited():
    symptoms = [{"code": f"SIM-{n}", "term": f"S{n}"} for n in range(MAX_SYMPTOMS + 1)]

    errors = validate_relatives({"relatives": [relative(symptoms=symptoms)]})

    assert "más de 30 síntomas" in errors[0]


class FakeQuery:
    def __init__(self, client):
        self.client = client
        self.operations = []

    def __getattr__(self, operation):
        def record(*args, **kwargs):
            self.operations.append(operation)
            self.args = args
            return self

        return record

    def execute(self):
        self.client.calls.append(
            (self.operations[-1] if self.operations[0] != "select" else "select", self.args)
        )
        data = self.client.listed if self.operations[0] == "select" else []
        return type("Result", (), {"data": data})


class FakeClient:
    def __init__(self, listed):
        self.listed = listed
        self.calls = []

    def table(self, name):
        assert name == "relatives"
        return FakeQuery(self)


def test_replacing_inserts_the_new_ones_before_deleting_the_old_ones(monkeypatch):
    client = FakeClient(listed=[{"id": 7}, {"id": 8}])
    monkeypatch.setattr(repository, "supabase_admin", client)

    repository.replace_all("p-1", [{"name": "Carolina"}])

    assert [call[0] for call in client.calls] == ["select", "insert", "in_"]
    assert client.calls[1][1] == ([{"name": "Carolina", "patient_id": "p-1"}],)
    assert client.calls[2][1] == ("id", [7, 8])


def test_replacing_with_an_empty_list_only_deletes_the_old_ones(monkeypatch):
    client = FakeClient(listed=[{"id": 7}])
    monkeypatch.setattr(repository, "supabase_admin", client)

    repository.replace_all("p-1", [])

    assert [call[0] for call in client.calls] == ["select", "in_"]


def test_replacing_when_there_was_nothing_only_inserts(monkeypatch):
    client = FakeClient(listed=[])
    monkeypatch.setattr(repository, "supabase_admin", client)

    repository.replace_all("p-1", [{"name": "Carolina"}])

    assert [call[0] for call in client.calls] == ["select", "insert"]
