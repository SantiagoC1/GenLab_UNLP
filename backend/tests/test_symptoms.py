import pytest

from app.core.enums import Rol
from app.integrations.snomed import SnomedReal

URL = "/consulta_medica/symptoms"
ALLOWED = [Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO]
FORBIDDEN = [rol for rol in Rol if rol not in ALLOWED]


class FakeSnomed:
    """Reemplaza al adaptador: registra lo que recibe y devuelve lo que se le indica."""

    def __init__(self, result=None, error=None):
        self.result = result if result is not None else {"items": [], "has_more": False}
        self.error = error
        self.calls = []

    def buscar_terminos(self, texto, pagina=1):
        self.calls.append((texto, pagina))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def snomed(monkeypatch):
    """Parcha el adaptador donde lo usa el servicio. Uso: `snomed(result=...)` o `snomed(error=...)`."""

    def _install(**kwargs):
        fake = FakeSnomed(**kwargs)
        monkeypatch.setattr("app.modules.consulta_medica.service.obtener_snomed", lambda: fake)
        return fake

    return _install


@pytest.mark.parametrize("rol", ALLOWED)
def test_medical_roles_can_search(client, login_as, snomed, rol):
    login_as(rol)
    snomed(result={"items": [{"code": "SIM-009", "term": "Hipotonía"}], "has_more": False})

    response = client.get(URL, params={"q": "hip"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"code": "SIM-009", "term": "Hipotonía"}],
        "page": 1,
        "has_more": False,
    }


@pytest.mark.parametrize("rol", FORBIDDEN)
def test_other_roles_cannot_search(client, login_as, snomed, rol):
    login_as(rol)
    snomed()

    assert client.get(URL, params={"q": "hip"}).status_code == 403


def test_requires_a_session(client):
    assert client.get(URL, params={"q": "hip"}).status_code == 401


def test_requires_the_password_to_be_changed_first(client, login_as, snomed):
    login_as(Rol.MEDICO_TRATANTE, must_change_password=True)
    snomed()

    assert client.get(URL, params={"q": "hip"}).status_code == 403


def test_the_session_is_checked_before_the_data(client):
    # sin sesión no se revela nada sobre qué valores son válidos
    assert client.get(URL, params={"q": "h", "page": "x"}).status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": ""},
        {"q": "hi"},
        {"q": "   "},
        {"q": "  ab  "},
        {"q": "a" * 101},
        {"q": "hip\nop"},
        {"q": "hip\x00"},
        {"q": "hip", "page": "0"},
        {"q": "hip", "page": "-1"},
        {"q": "hip", "page": "abc"},
        {"q": "hip", "page": "1.5"},
        {"q": "hip", "page": ""},
        {"q": "hip", "page": "101"},
        {"q": "hip", "page": "٣"},
        {"q": "hip", "page": "1" * 20},
    ],
)
def test_invalid_data_answers_422_in_spanish(client, login_as, snomed, params):
    login_as(Rol.MEDICO_TRATANTE)
    fake = snomed()

    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert "detalle" in response.json()
    assert fake.calls == [], "con datos inválidos no se consulta a SNOMED"


def test_all_the_errors_come_together(client, login_as, snomed):
    login_as(Rol.MEDICO_TRATANTE)
    snomed()

    detail = client.get(URL, params={"q": "hi", "page": "0"}).json()["detalle"]

    assert "al menos 3 letras" in detail and "página" in detail


def test_the_text_is_trimmed_before_it_reaches_snomed(client, login_as, snomed):
    login_as(Rol.GERENTE_MEDICO)
    fake = snomed()

    assert client.get(URL, params={"q": "  hip  ", "page": "2"}).status_code == 200
    assert fake.calls == [("hip", 2)]


def test_special_characters_reach_snomed_as_literal_text(client, login_as, snomed):
    login_as(Rol.GERENTE_MEDICO)
    fake = snomed()

    assert client.get(URL, params={"q": "a&b=c#%_'"}).status_code == 200
    assert fake.calls == [("a&b=c#%_'", 1)]


def test_no_matches_is_an_empty_page_and_not_an_error(client, login_as, snomed):
    login_as(Rol.MEDICO_TRATANTE)
    snomed()

    response = client.get(URL, params={"q": "zzzz"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "has_more": False}


def test_only_the_known_fields_are_returned(client, login_as, snomed):
    login_as(Rol.MEDICO_TRATANTE)
    snomed(
        result={
            "items": [{"code": 123, "term": "x" * 500, "interno": "secreto"}],
            "has_more": 1,
            "otro": "dato",
        }
    )

    body = client.get(URL, params={"q": "hip"}).json()

    assert body["items"] == [{"code": "123", "term": "x" * 200}]
    assert body["has_more"] is True
    assert set(body) == {"items", "page", "has_more"}


@pytest.mark.parametrize(
    "error",
    [NotImplementedError("x"), OSError("x"), TimeoutError("x"), ValueError("x"), KeyError("x")],
)
def test_a_failing_snomed_answers_503_without_details(client, login_as, snomed, error):
    login_as(Rol.MEDICO_TRATANTE)
    snomed(error=error)

    response = client.get(URL, params={"q": "hip"})

    assert response.status_code == 503
    assert response.json()["detalle"] == "El módulo externo 'SNOMED' no está disponible."


def test_a_malformed_answer_from_snomed_answers_503(client, login_as, snomed):
    login_as(Rol.MEDICO_TRATANTE)
    snomed(result={"sin": "items"})

    assert client.get(URL, params={"q": "hip"}).status_code == 503


def test_with_the_real_client_not_implemented_answers_503(client, login_as, monkeypatch):
    # Temporal: cuando exista el cliente real de SNOMED, este test se reemplaza por los suyos.
    login_as(Rol.MEDICO_TRATANTE)
    monkeypatch.setattr("app.modules.consulta_medica.service.obtener_snomed", lambda: SnomedReal())

    assert client.get(URL, params={"q": "hip"}).status_code == 503


def test_end_to_end_with_the_simulator(client, login_as):
    login_as(Rol.MEDICO_TRATANTE)

    body = client.get(URL, params={"q": "HIPOTONIA"}).json()

    assert body == {
        "items": [{"code": "SIM-009", "term": "Hipotonía"}],
        "page": 1,
        "has_more": False,
    }
