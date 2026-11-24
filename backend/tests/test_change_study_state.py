import pytest

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError
from app.modules.consulta_medica import service


@pytest.fixture
def store(monkeypatch):
    """Un estudio en memoria en lugar de Supabase, con su historial."""
    data = {"study": {"id": 1, "state": "Creado"}, "history": [], "concurrent": False}

    def find_study(study_id):
        return data["study"] if study_id == 1 else None

    def change(study_id, from_state, to_state, changed_by):
        if data["concurrent"]:
            return None
        data["study"]["state"] = to_state
        data["history"].append((from_state, to_state, changed_by))
        return data["study"]

    monkeypatch.setattr("app.modules.consulta_medica.repository.find_study", find_study)
    monkeypatch.setattr("app.modules.consulta_medica.repository.change_study_state", change)
    return data


def test_a_valid_change_updates_the_state_and_the_history(store):
    service.change_study_state(1, EstadoEstudio.PAGADO, "u-1")

    assert store["study"]["state"] == "Pagado"
    assert store["history"] == [("Creado", "Pagado", "u-1")]


def test_an_external_signal_leaves_changed_by_empty(store):
    service.change_study_state(1, EstadoEstudio.AUTORIZADO)

    assert store["history"] == [("Creado", "Autorizado", None)]


def test_an_invalid_transition_is_rejected_and_nothing_changes(store):
    with pytest.raises(BusinessRuleError) as error:
        service.change_study_state(1, EstadoEstudio.RESULTADO_DISPONIBLE, "u-1")

    assert error.value.code == "transicion_invalida"
    assert store["study"]["state"] == "Creado"
    assert store["history"] == []


def test_an_unknown_study_answers_404(store):
    with pytest.raises(BusinessRuleError) as error:
        service.change_study_state(99, EstadoEstudio.PAGADO)

    assert error.value.status_code == 404


def test_a_concurrent_change_is_reported(store):
    store["concurrent"] = True

    with pytest.raises(BusinessRuleError) as error:
        service.change_study_state(1, EstadoEstudio.PAGADO)

    assert error.value.status_code == 409
