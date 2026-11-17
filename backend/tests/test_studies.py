from datetime import date, timedelta

import pytest

from app.core.enums import Rol
from app.modules.consulta_medica import service

GENES_URL = "/consulta_medica/studies/genes"
STUDIES_URL = "/consulta_medica/studies"
NOT_DOCTORS = [rol for rol in Rol if rol != Rol.MEDICO_TRATANTE]

PATIENT_ID = "123e4567-e89b-12d3-a456-426614174000"
FABRY = {"id": 1, "name": "Fabry", "cardinal": None, "secondary": []}
POMPE = {"id": 2, "name": "Pompe", "cardinal": None, "secondary": []}
GENES_OF = {"Fabry": ["GLA"], "Pompe": ["GAA"]}


def adult_birth_date():
    return "1990-05-20"


def baby_birth_date():
    return (date.today() - timedelta(days=30)).isoformat()


class World:
    """Reemplaza al repositorio, al catálogo de patologías y a Apigen con datos en memoria.

    Guarda lo que se intentó crear, para que los tests comprueben que, si falla algo, no se creó nada.
    """

    def __init__(self):
        self.patient = {
            "id": PATIENT_ID,
            "dni": "30123456",
            "first_name": "Ana",
            "last_name": "Pérez",
            "birth_date": adult_birth_date(),
        }
        self.apigen_error = None
        self.apigen_calls = []
        self.created_studies = []
        self.genes_of = GENES_OF

    def find_by_id(self, patient_id):
        return self.patient if patient_id == self.patient["id"] else None

    def create_study(self, row, pathology_ids, genes):
        self.created_studies.append((row, pathology_ids, genes))
        return {"id": 12, "state": "Creado", **row}

    def genes_por_patologia(self, name, with_secondary=False):
        self.apigen_calls.append((name, with_secondary))
        if self.apigen_error:
            raise self.apigen_error
        return self.genes_of[name] + (["ACMG-1"] if with_secondary else [])


@pytest.fixture
def world(monkeypatch):
    fake = World()
    monkeypatch.setattr("app.modules.config_medica.repository.list_all", lambda: [FABRY, POMPE])
    monkeypatch.setattr("app.modules.consulta_medica.repository.find_by_id", fake.find_by_id)
    monkeypatch.setattr("app.modules.consulta_medica.repository.create_study", fake.create_study)
    monkeypatch.setattr(
        service,
        "obtener_apigen",
        lambda: type(
            "Apigen", (), {"genes_por_patologia": staticmethod(fake.genes_por_patologia)}
        )(),
    )
    return fake


def valid_study(**changes):
    study = {"patient_id": PATIENT_ID, "pathology_ids": [1], "secondary_findings": False}
    return {**study, **changes}


def genes_of(response):
    return [(gene["gene"], gene["origin"]) for gene in response.json()["genes"]]


def test_the_preview_lists_the_genes_of_the_pathologies(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.get(GENES_URL, params={"pathology_ids": "1"})

    assert response.status_code == 200
    assert genes_of(response) == [("GLA", "patologia")]


def test_the_preview_adds_the_secondary_findings_when_asked(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.get(GENES_URL, params={"pathology_ids": "1", "secondary_findings": "true"})

    assert genes_of(response) == [("GLA", "patologia"), ("ACMG-1", "hallazgo_secundario")]


def test_the_preview_joins_several_pathologies_without_repeating_genes(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.genes_of = {"Fabry": ["GLA", "GAA"], "Pompe": ["GAA"]}

    response = client.get(GENES_URL, params={"pathology_ids": "1,2"})

    assert genes_of(response) == [("GLA", "patologia"), ("GAA", "patologia")]


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "al menos una patología"),
        ({"pathology_ids": ""}, "al menos una patología"),
        ({"pathology_ids": "abc"}, "al menos una patología"),
        ({"pathology_ids": "1,1"}, "no pueden repetirse"),
        ({"pathology_ids": "99"}, "no está en el catálogo"),
        ({"pathology_ids": "1", "secondary_findings": "quizás"}, "true o false"),
    ],
)
def test_the_preview_checks_its_parameters(client, login_as, world, params, message):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.get(GENES_URL, params=params)

    assert response.status_code == 422
    assert message in response.json()["detalle"]


def test_the_preview_answers_503_when_apigen_is_down(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.apigen_error = NotImplementedError("contrato pendiente")

    response = client.get(GENES_URL, params={"pathology_ids": "1"})

    assert response.status_code == 503
    assert "Apigen" in response.json()["detalle"]


def test_a_study_is_created_in_state_creado_with_its_genes(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(STUDIES_URL, json=valid_study(secondary_findings=True))

    assert response.status_code == 201
    body = response.json()
    assert (body["id"], body["state"], body["pompe_urgent"]) == (12, "Creado", False)
    assert genes_of(response) == [("GLA", "patologia"), ("ACMG-1", "hallazgo_secundario")]
    row, pathology_ids, genes = world.created_studies[0]
    assert row["patient_id"] == PATIENT_ID
    assert row["requested_by"] == "u-sesion"
    assert row["secondary_findings"] is True
    assert pathology_ids == [1]
    assert [gene["origin"] for gene in genes] == ["patologia", "hallazgo_secundario"]


def test_the_genes_are_asked_to_apigen_again_on_the_server(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    payload = valid_study(genes=[{"gene": "FALSO", "origin": "patologia"}])

    response = client.post(STUDIES_URL, json=payload)

    assert genes_of(response) == [("GLA", "patologia")]
    assert world.apigen_calls == [("Fabry", False)]


def test_manual_genes_are_added_in_uppercase_without_repeating(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(
        STUDIES_URL, json=valid_study(manual_genes=["gaa", " GAA ", "gla", "  "])
    )

    assert response.status_code == 201
    assert genes_of(response) == [("GLA", "patologia"), ("GAA", "manual")]


def test_a_study_with_several_pathologies_is_saved_with_all_of_them(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(STUDIES_URL, json=valid_study(pathology_ids=[1, 2]))

    assert response.status_code == 201
    assert genes_of(response) == [("GLA", "patologia"), ("GAA", "patologia")]
    assert world.created_studies[0][1] == [1, 2]


def test_pompe_in_a_baby_marks_the_study_as_urgent(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patient["birth_date"] = baby_birth_date()

    response = client.post(STUDIES_URL, json=valid_study(pathology_ids=[2]))

    assert response.json()["pompe_urgent"] is True
    assert world.created_studies[0][0]["pompe_urgent"] is True


def test_a_baby_without_pompe_is_not_urgent(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patient["birth_date"] = baby_birth_date()

    response = client.post(STUDIES_URL, json=valid_study(pathology_ids=[1]))

    assert response.json()["pompe_urgent"] is False


def test_pompe_in_an_adult_is_not_urgent(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(STUDIES_URL, json=valid_study(pathology_ids=[2]))

    assert response.json()["pompe_urgent"] is False


def test_a_study_for_an_unknown_patient_answers_404(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    other_patient = "123e4567-e89b-12d3-a456-426614174999"

    response = client.post(STUDIES_URL, json=valid_study(patient_id=other_patient))

    assert response.status_code == 404
    assert world.created_studies == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"patient_id": None}, "Elegí al paciente"),
        ({"patient_id": "no-es-un-uuid"}, "paciente no es válido"),
        ({"pathology_ids": []}, "al menos un diagnóstico"),
        ({"pathology_ids": None}, "al menos un diagnóstico"),
        ({"pathology_ids": [1, 1]}, "no pueden repetirse"),
        ({"pathology_ids": [99]}, "no está en el catálogo"),
    ],
)
def test_the_study_data_is_checked(client, login_as, world, changes, message):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(STUDIES_URL, json=valid_study(**changes))

    assert response.status_code == 422
    assert message in response.json()["detalle"]
    assert world.created_studies == []


def test_without_apigen_no_study_is_created(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.apigen_error = NotImplementedError("contrato pendiente")

    response = client.post(STUDIES_URL, json=valid_study())

    assert response.status_code == 503
    assert world.created_studies == []


@pytest.mark.parametrize("rol", NOT_DOCTORS)
def test_only_the_treating_doctor_can_use_the_study_routes(client, login_as, world, rol):
    login_as(rol)

    assert client.get(GENES_URL, params={"pathology_ids": "1"}).status_code == 403
    assert client.post(STUDIES_URL, json=valid_study()).status_code == 403
    assert world.created_studies == []


def test_the_study_routes_require_a_session(client, world):
    assert client.get(GENES_URL, params={"pathology_ids": "1"}).status_code == 401
    assert client.post(STUDIES_URL, json=valid_study()).status_code == 401


@pytest.mark.parametrize(
    ("birth_date", "today", "months"),
    [
        (date(2026, 7, 14), date(2026, 11, 13), 3),
        (date(2026, 7, 14), date(2026, 11, 14), 4),
        (date(2026, 7, 14), date(2026, 11, 15), 4),
        (date(2025, 11, 14), date(2026, 11, 14), 12),
        (date(2026, 11, 14), date(2026, 11, 14), 0),
    ],
)
def test_months_old_counts_whole_months(birth_date, today, months):
    assert service.months_old(birth_date, today) == months


@pytest.mark.parametrize(
    ("pathology_name", "today", "urgent"),
    [
        ("Pompe", date(2026, 11, 13), True),
        ("pompe", date(2026, 11, 13), True),
        ("Enfermedad de Pompe", date(2026, 11, 13), True),
        ("Pompe", date(2026, 11, 14), False),
        ("Fabry", date(2026, 11, 13), False),
    ],
)
def test_pompe_is_urgent_only_under_four_months(pathology_name, today, urgent):
    birth_date = date(2026, 7, 14)
    pathologies = [{"id": 1, "name": pathology_name}]

    assert service.is_pompe_urgent(birth_date, pathologies, today) is urgent


def test_pompe_among_other_pathologies_is_urgent():
    pathologies = [{"id": 1, "name": "Fabry"}, {"id": 2, "name": "Pompe"}]

    assert service.is_pompe_urgent(date(2026, 7, 14), pathologies, date(2026, 11, 13)) is True
