import pytest

from app.core.enums import CdssStrategy, Rol

URL = "/config_medica/cdss-strategy"
NOT_MANAGERS = [rol for rol in Rol if rol != Rol.GERENTE_MEDICO]


class FakeSettings:
    def __init__(self, value=None):
        self.value = value
        self.saved = []

    def get(self, key):
        return self.value

    def save(self, key, value, user_id):
        self.saved.append((key, value, user_id))
        self.value = value


@pytest.fixture
def settings(monkeypatch):
    def _install(value=None):
        fake = FakeSettings(value)
        monkeypatch.setattr("app.models.app_setting.get", fake.get)
        monkeypatch.setattr("app.models.app_setting.save", fake.save)
        return fake

    return _install


def test_without_a_saved_value_the_default_strategy_is_used(client, login_as, settings):
    login_as(Rol.GERENTE_MEDICO)
    settings()

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"strategy": "sintomas_cardinales_coincidentes"}


def test_the_saved_strategy_is_returned(client, login_as, settings):
    login_as(Rol.GERENTE_MEDICO)
    settings("menor_diferencia")

    assert client.get(URL).json() == {"strategy": "menor_diferencia"}


@pytest.mark.parametrize("strategy", list(CdssStrategy))
def test_the_manager_can_choose_each_strategy(client, login_as, settings, strategy):
    user = login_as(Rol.GERENTE_MEDICO)
    fake = settings()

    response = client.put(URL, json={"strategy": strategy.value})

    assert response.status_code == 200
    assert response.json() == {"strategy": strategy.value}
    assert fake.saved == [("cdss_strategy", strategy.value, user["id"])]


@pytest.mark.parametrize("strategy", [None, "", "otra", 3])
def test_an_unknown_strategy_is_rejected(client, login_as, settings, strategy):
    login_as(Rol.GERENTE_MEDICO)
    fake = settings()

    response = client.put(URL, json={"strategy": strategy})

    assert response.status_code == 422
    assert fake.saved == []


@pytest.mark.parametrize("role", NOT_MANAGERS)
def test_only_the_manager_can_read_or_change_it(client, login_as, settings, role):
    login_as(role)
    fake = settings()

    assert client.get(URL).status_code == 403
    assert client.put(URL, json={"strategy": "menor_diferencia"}).status_code == 403
    assert fake.saved == []


def test_it_requires_a_session(client, settings):
    settings()

    assert client.get(URL).status_code == 401
    assert client.put(URL, json={"strategy": "menor_diferencia"}).status_code == 401
