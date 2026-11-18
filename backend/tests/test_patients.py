from datetime import date, timedelta

import pytest

from app.core.enums import Rol
from app.modules.consulta_medica import repository as patient_repository
from app.modules.consulta_medica import service

URL = "/consulta_medica/patients"
NOT_DOCTORS = [rol for rol in Rol if rol != Rol.MEDICO_TRATANTE]

PAIN = {"code": "SIM-001", "term": "Dolor"}
FEVER = {"code": "SIM-002", "term": "Fiebre"}
FABRY = {"id": 1, "name": "Fabry", "code": "FABRY", "cardinal": PAIN, "secondary": [FEVER]}
POMPE = {"id": 2, "name": "Pompe", "code": "POMPE", "cardinal": FEVER, "secondary": [PAIN]}
ADULT_BIRTH_DATE = "1990-05-20"


def valid_payload(**changes):
    payload = {
        "dni": "30123456",
        "first_name": "Ana",
        "last_name": "Pérez",
        "birth_date": ADULT_BIRTH_DATE,
        "phone": "2215550000",
        "email": "ana@ejemplo.com",
        "suspicion_type": "clinica",
        "pathology_ids": [1],
        "clinical_summary": "Dolor en manos y pies desde la infancia.",
        "symptoms": [PAIN],
    }
    return {**payload, **changes}


class World:
    """Reemplaza al modelo de pacientes, a los usuarios, al CDSS y a los avisos con datos en memoria.

    Guarda lo que se creó y lo que se deshizo, para que los tests comprueben las compensaciones.
    """

    def __init__(self):
        self.patients = {}
        self.users = {}
        self.created_patients = []
        self.deleted_patients = []
        self.created_accounts = []
        self.deleted_accounts = []
        self.mails = []
        self.cdss_answer = ["FABRY"]
        self.cdss_error = None
        self.cdss_calls = []
        self.mail_works = True
        self.patient_create_error = None
        self.delete_patient_error = None

    def find_by_dni(self, dni):
        return self.patients.get(dni)

    def create_patient(self, row, pathology_ids, symptoms):
        if self.patient_create_error:
            raise self.patient_create_error
        patient = {"id": "p-1", **row}
        self.created_patients.append((row, pathology_ids, symptoms))
        return patient

    def delete_patient(self, patient_id):
        if self.delete_patient_error:
            raise self.delete_patient_error
        self.deleted_patients.append(patient_id)

    def find_by_email(self, email):
        return self.users.get(email)

    def create_account(self, data, password, must_change_password):
        self.created_accounts.append((data, must_change_password))
        return {"id": "u-nuevo", **data}

    def delete_account(self, user_id):
        self.deleted_accounts.append(user_id)

    def ask_cdss(self, codes, strategy):
        self.cdss_calls.append((codes, strategy))
        if self.cdss_error:
            raise self.cdss_error
        return self.cdss_answer

    def send_mail(self, to, channel, message):
        self.mails.append((to, message))
        return self.mail_works


@pytest.fixture
def world(monkeypatch):
    fake = World()
    monkeypatch.setattr("app.modules.consulta_medica.repository.find_by_dni", fake.find_by_dni)
    monkeypatch.setattr("app.modules.consulta_medica.repository.create", fake.create_patient)
    monkeypatch.setattr("app.modules.consulta_medica.repository.delete", fake.delete_patient)
    monkeypatch.setattr("app.modules.config_medica.repository.list_all", lambda: [FABRY, POMPE])
    monkeypatch.setattr("app.modules.acceso.repository.find_by_email", fake.find_by_email)
    monkeypatch.setattr(service, "create_account", fake.create_account)
    monkeypatch.setattr(service, "_delete_account", fake.delete_account)
    monkeypatch.setattr(service, "get_cdss_strategy", lambda: "menor_diferencia")
    monkeypatch.setattr(
        service,
        "obtener_cdss",
        lambda: type("Cdss", (), {"sintomas_a_patologia": staticmethod(fake.ask_cdss)})(),
    )
    monkeypatch.setattr(
        service,
        "obtener_avisos",
        lambda: type("Avisos", (), {"enviar_aviso": staticmethod(fake.send_mail)})(),
    )
    return fake


def years_ago(years, extra_days=0):
    """Fecha de nacimiento de alguien que cumplió `years` años hace `extra_days` días."""
    today = date.today()
    return (today.replace(year=today.year - years) - timedelta(days=extra_days)).isoformat()


def test_an_adult_gets_an_account_and_the_credentials_by_mail(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 201
    assert response.json()["account_created"] is True
    account, must_change_password = world.created_accounts[0]
    assert account["role"] == "paciente"
    assert account["email"] == "ana@ejemplo.com"
    assert must_change_password is True
    assert [to for to, _ in world.mails] == ["ana@ejemplo.com"]
    row, pathology_ids, symptoms = world.created_patients[0]
    assert row["account_user_id"] == "u-nuevo"
    assert row["registered_by"] == "u-sesion"
    assert (pathology_ids, symptoms) == ([1], [PAIN])


def test_the_response_does_not_include_the_password(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload())

    assert "contraseña" not in response.text
    assert set(response.json()) == {
        "id",
        "dni",
        "first_name",
        "last_name",
        "birth_date",
        "account_created",
    }


def test_a_minor_gets_an_account_with_the_mail_of_the_parents(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    payload = valid_payload(birth_date=years_ago(10), email="padres@ejemplo.com")

    response = client.post(URL, json=payload)

    assert response.status_code == 201
    account, _ = world.created_accounts[0]
    assert account["email"] == "padres@ejemplo.com"
    assert account["first_name"] == "Ana"
    assert [to for to, _ in world.mails] == ["padres@ejemplo.com"]


def test_a_minor_reuses_the_account_of_a_sibling_and_no_mail_is_sent(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.users["padres@ejemplo.com"] = {"id": "u-hermano", "role": "paciente"}
    payload = valid_payload(birth_date=years_ago(5), email="padres@ejemplo.com")

    response = client.post(URL, json=payload)

    assert response.status_code == 201
    assert response.json()["account_created"] is False
    assert world.created_accounts == []
    assert world.mails == []
    assert world.created_patients[0][0]["account_user_id"] == "u-hermano"


def test_a_minor_cannot_use_the_mail_of_a_user_that_is_not_a_patient(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.users["padres@ejemplo.com"] = {"id": "u-medico", "role": "medico_tratante"}
    payload = valid_payload(birth_date=years_ago(5), email="padres@ejemplo.com")

    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["detalle"] == service.EMAIL_UNAVAILABLE
    assert world.created_patients == []


@pytest.mark.parametrize("role", ["paciente", "medico_tratante"])
def test_an_adult_cannot_use_a_mail_that_already_exists(client, login_as, world, role):
    login_as(Rol.MEDICO_TRATANTE)
    world.users["ana@ejemplo.com"] = {"id": "u-otro", "role": role}

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 422
    assert response.json()["detalle"] == service.EMAIL_UNAVAILABLE
    assert (world.created_patients, world.created_accounts, world.mails) == ([], [], [])


def test_the_rejection_does_not_say_which_role_the_mail_has(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.users["padres@ejemplo.com"] = {"id": "u-medico", "role": "medico_tratante"}
    world.users["ana@ejemplo.com"] = {"id": "u-paciente", "role": "paciente"}
    minor = valid_payload(birth_date=years_ago(5), email="padres@ejemplo.com")

    first = client.post(URL, json=minor)
    second = client.post(URL, json=valid_payload())

    assert first.status_code == second.status_code == 422
    assert first.json() == second.json()


def test_a_familial_suspicion_can_go_without_symptoms_and_skips_the_cdss(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(suspicion_type="familiar", symptoms=[]))

    assert response.status_code == 201
    assert world.cdss_calls == []


def test_the_cdss_receives_the_symptom_codes_and_the_configured_strategy(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    client.post(URL, json=valid_payload(symptoms=[PAIN, FEVER]))

    assert world.cdss_calls == [(["SIM-001", "SIM-002"], "menor_diferencia")]


def test_the_alta_is_blocked_when_the_cdss_points_to_another_pathology(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.cdss_answer = ["POMPE"]

    response = client.post(URL, json=valid_payload(pathology_ids=[1]))

    assert response.status_code == 422
    detail = response.json()["detalle"]
    assert "no corresponden" in detail
    assert "POMPE" in detail
    assert "«Dolor»" in detail
    assert (world.created_patients, world.created_accounts, world.mails) == ([], [], [])


def test_the_alta_is_blocked_when_the_cdss_says_it_is_not_compatible(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.cdss_answer = []

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 422
    assert "no corresponden" in response.json()["detalle"]


def test_it_is_enough_that_the_cdss_matches_one_of_the_chosen_pathologies(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.cdss_answer = ["pompe"]

    response = client.post(URL, json=valid_payload(pathology_ids=[1, 2]))

    assert response.status_code == 201


def test_a_tie_in_the_cdss_is_accepted_if_one_of_the_tied_is_chosen(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.cdss_answer = ["POMPE", "FABRY"]

    response = client.post(URL, json=valid_payload(pathology_ids=[1]))

    assert response.status_code == 201


def test_without_the_cdss_nothing_is_created(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.cdss_error = NotImplementedError("contrato pendiente")

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 503
    assert "CDSS" in response.json()["detalle"]
    assert (world.created_patients, world.created_accounts, world.mails) == ([], [], [])


def test_an_existing_dni_answers_409_with_a_code(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patients["30123456"] = {"id": "p-0"}

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 409
    assert response.json()["code"] == "patient_exists"
    assert world.created_accounts == []


def test_a_dni_taken_in_between_deletes_the_new_account(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patient_create_error = patient_repository.DniTaken()

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 409
    assert world.deleted_accounts == ["u-nuevo"]


def test_a_failure_saving_the_patient_deletes_the_new_account(login_as, world):
    from fastapi.testclient import TestClient

    from app.main import app

    login_as(Rol.MEDICO_TRATANTE)
    world.patient_create_error = RuntimeError("falló la base")

    response = TestClient(app, raise_server_exceptions=False).post(URL, json=valid_payload())

    assert response.status_code == 500
    assert world.deleted_accounts == ["u-nuevo"]


def test_if_the_mail_fails_the_patient_and_the_account_are_deleted(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.mail_works = False

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 503
    assert world.deleted_patients == ["p-1"]
    assert world.deleted_accounts == ["u-nuevo"]


def test_a_mail_that_raises_is_treated_as_a_failed_send(client, login_as, world, monkeypatch):
    login_as(Rol.MEDICO_TRATANTE)

    def broken_send(to, channel, message):
        raise ConnectionError("sin red")

    monkeypatch.setattr(
        service,
        "obtener_avisos",
        lambda: type("Avisos", (), {"enviar_aviso": staticmethod(broken_send)})(),
    )

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 503
    assert world.deleted_patients == ["p-1"]
    assert world.deleted_accounts == ["u-nuevo"]


def test_the_simulator_does_not_log_the_initial_password(client, login_as, world, caplog):
    login_as(Rol.MEDICO_TRATANTE)

    with caplog.at_level("WARNING", logger=service.logger.name):
        client.post(URL, json=valid_payload())

    password = world.mails[0][1].split("contraseña inicial ")[1].split(". ")[0]
    assert password not in caplog.text
    assert "ana@ejemplo.com" in caplog.text


def test_deleting_an_account_only_removes_the_auth_user(monkeypatch):
    calls = []
    admin = type("Admin", (), {"delete_user": staticmethod(calls.append)})()
    monkeypatch.setattr(service.supabase_admin, "auth", type("Auth", (), {"admin": admin})())

    service._delete_account("u-1")

    assert calls == ["u-1"]


def test_if_the_mail_fails_a_reused_account_is_not_deleted(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.users["padres@ejemplo.com"] = {"id": "u-hermano", "role": "paciente"}
    world.mail_works = False
    payload = valid_payload(birth_date=years_ago(5), email="padres@ejemplo.com")

    response = client.post(URL, json=payload)

    assert response.status_code == 201
    assert world.deleted_accounts == []


@pytest.mark.parametrize(
    "field",
    [
        "dni",
        "first_name",
        "last_name",
        "birth_date",
        "phone",
        "email",
        "suspicion_type",
        "clinical_summary",
    ],
)
def test_every_required_field_is_checked(client, login_as, world, field):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(**{field: "  "}))

    assert response.status_code == 422
    assert "es obligatorio" in response.json()["detalle"]
    assert world.created_patients == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"dni": "123456"}, "7 u 8 dígitos"),
        ({"dni": "123456789"}, "7 u 8 dígitos"),
        ({"dni": "12.345.678"}, "7 u 8 dígitos"),
        ({"email": "sin-arroba"}, "formato válido"),
        ({"birth_date": "20/05/1990"}, "fecha de nacimiento no es válida"),
        ({"birth_date": (date.today() + timedelta(days=1)).isoformat()}, "no puede ser futura"),
        ({"suspicion_type": "otra"}, "clínica o familiar"),
        ({"pathology_ids": []}, "al menos un diagnóstico"),
        ({"pathology_ids": [1, 1]}, "no pueden repetirse"),
        ({"pathology_ids": [99]}, "no está en el catálogo"),
        ({"symptoms": []}, "al menos un síntoma"),
        ({"symptoms": [{"code": "SIM-001"}]}, "síntoma que no es válido"),
        ({"symptoms": [PAIN, PAIN]}, "no pueden repetirse"),
    ],
)
def test_the_formats_are_checked(client, login_as, world, changes, message):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(**changes))

    assert response.status_code == 422
    assert message in response.json()["detalle"]
    assert world.created_patients == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"first_name": "A" * 101}, "'nombre' no puede tener más de 100"),
        ({"last_name": "A" * 101}, "'apellido' no puede tener más de 100"),
        ({"phone": "1" * 31}, "'teléfono' no puede tener más de 30"),
        ({"email": "a" * 250 + "@x.com"}, "'mail' no puede tener más de 254"),
        ({"clinical_summary": "A" * 5001}, "no puede tener más de 5000"),
        ({"first_name": "Ana\nPérez"}, "'nombre' tiene caracteres que no se pueden usar"),
        ({"phone": "221\x00555"}, "'teléfono' tiene caracteres que no se pueden usar"),
    ],
)
def test_the_size_and_characters_of_the_texts_are_checked(
    client, login_as, world, changes, message
):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(**changes))

    assert response.status_code == 422
    assert message in response.json()["detalle"]
    assert world.created_patients == []


def test_the_clinical_summary_can_have_several_lines(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(clinical_summary="Línea 1\nLínea 2"))

    assert response.status_code == 201


def test_the_search_by_dni_only_asks_for_the_minimal_columns(monkeypatch):
    asked = []

    class Query:
        def select(self, columns):
            asked.append(columns)
            return self

        def eq(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            return type("Response", (), {"data": []})()

    monkeypatch.setattr(patient_repository, "_table", lambda _name: Query())

    patient_repository.find_by_dni("30123456")

    assert asked == ["id, dni, first_name, last_name, birth_date"]


def test_a_birth_date_of_today_is_valid(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json=valid_payload(birth_date=date.today().isoformat()))

    assert response.status_code == 201


def test_all_the_errors_come_together(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    response = client.post(URL, json={})

    detail = response.json()["detalle"]
    assert response.status_code == 422
    assert "DNI" in detail
    assert "mail" in detail
    assert "diagnóstico presuntivo" in detail


@pytest.mark.parametrize("rol", NOT_DOCTORS)
def test_only_the_treating_doctor_can_create_a_patient(client, login_as, world, rol):
    login_as(rol)

    assert client.post(URL, json=valid_payload()).status_code == 403
    assert world.created_patients == []


def test_creating_a_patient_requires_a_session(client, world):
    assert client.post(URL, json=valid_payload()).status_code == 401


def test_a_patient_is_found_by_dni_with_minimal_data(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)
    world.patients["30123456"] = {
        "id": "p-9",
        "dni": "30123456",
        "first_name": "Ana",
        "last_name": "Pérez",
        "birth_date": ADULT_BIRTH_DATE,
        "clinical_summary": "dato clínico que no se tiene que devolver",
    }

    response = client.get(URL, params={"dni": "30123456"})

    assert response.status_code == 200
    assert "clinical_summary" not in response.json()
    assert response.json()["first_name"] == "Ana"


def test_an_unknown_dni_answers_404(client, login_as, world):
    login_as(Rol.MEDICO_TRATANTE)

    assert client.get(URL, params={"dni": "30123456"}).status_code == 404


@pytest.mark.parametrize("params", [{}, {"dni": "abc"}, {"dni": "123"}])
def test_the_search_requires_a_valid_dni(client, login_as, world, params):
    login_as(Rol.MEDICO_TRATANTE)

    assert client.get(URL, params=params).status_code == 422


@pytest.mark.parametrize("rol", NOT_DOCTORS)
def test_only_the_treating_doctor_can_search_patients(client, login_as, world, rol):
    login_as(rol)

    assert client.get(URL, params={"dni": "30123456"}).status_code == 403


def test_is_minor_the_day_before_the_18th_birthday():
    today = date(2026, 11, 14)

    assert service.is_minor(date(2008, 11, 15), today) is True


def test_is_adult_on_the_18th_birthday():
    today = date(2026, 11, 14)

    assert service.is_minor(date(2008, 11, 14), today) is False
