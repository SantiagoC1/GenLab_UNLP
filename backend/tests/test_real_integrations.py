"""Clientes reales de SNOMED, del CDSS y de Apigen, con HTTP simulado."""

import base64

import httpx
import pytest

from app.core.config import get_settings
from app.integrations import apigen, cdss, familiograma, snomed
from app.integrations.apigen import ApigenReal
from app.integrations.cdss import CdssReal
from app.integrations.familiograma import (
    FamiliogramaInvalido,
    FamiliogramaReal,
    FamiliogramaSimulador,
)
from app.integrations.snomed import PAGE_SIZE, SnomedReal


class FakeResponse:
    """Respuesta HTTP mínima: el JSON y, si hace falta, un error."""

    def __init__(self, data=None, status=200):
        self._data = data
        self.status = status
        self.status_code = status

    def raise_for_status(self):
        if self.status >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._data


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("SNOMED_URL", "https://snomed.test/sintomas")
    monkeypatch.setenv("SNOMED_APIKEY", "clave-snomed")
    monkeypatch.setenv("CDSS_URL", "https://cdss.test/api/v1/")
    monkeypatch.setenv("CDSS_APIKEY", "clave-cdss")
    monkeypatch.setenv("APIGEN_URL", "https://apigen.test/rest/v1/")
    monkeypatch.setenv("APIGEN_APIKEY", "clave-apigen")
    monkeypatch.setenv("FAMILIOGRAMA_URL", "https://familiograma.test/v1/")
    monkeypatch.setenv("FAMILIOGRAMA_APIKEY", "clave-familiograma")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def found(n):
    return {"sctid": 1000 + n, "termino_preferido": f"Síntoma {n}", "estrategia": "prefijo"}


def test_snomed_asks_with_the_key_and_maps_the_fields(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"resultados": [found(1)]})

    monkeypatch.setattr(snomed.httpx, "get", fake_get)

    result = SnomedReal().buscar_terminos("sinto")

    assert result == {"items": [{"code": "1001", "term": "Síntoma 1"}], "has_more": False}
    url, kwargs = calls[0]
    assert url == "https://snomed.test/sintomas"
    assert kwargs["params"] == {"q": "sinto", "limite": 50}
    assert kwargs["headers"] == {"X-API-Key": "clave-snomed", "x-region": "us-east-1"}


def test_snomed_code_is_always_text(monkeypatch):
    monkeypatch.setattr(
        snomed.httpx, "get", lambda *a, **k: FakeResponse({"resultados": [found(1)]})
    )

    assert isinstance(SnomedReal().buscar_terminos("sinto")["items"][0]["code"], str)


def test_snomed_paginates_the_results_here(monkeypatch):
    results = [found(n) for n in range(PAGE_SIZE + 3)]
    monkeypatch.setattr(snomed.httpx, "get", lambda *a, **k: FakeResponse({"resultados": results}))

    first = SnomedReal().buscar_terminos("sinto", 1)
    second = SnomedReal().buscar_terminos("sinto", 2)

    assert len(first["items"]) == PAGE_SIZE and first["has_more"] is True
    assert len(second["items"]) == 3 and second["has_more"] is False


def test_snomed_with_an_error_status_raises(monkeypatch):
    monkeypatch.setattr(snomed.httpx, "get", lambda *a, **k: FakeResponse(status=503))

    with pytest.raises(httpx.HTTPStatusError):
        SnomedReal().buscar_terminos("sinto")


def test_cdss_sets_the_strategy_and_then_asks(monkeypatch):
    calls = []

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return FakeResponse({})

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return FakeResponse({"patologias": [{"codigo": "FABRY", "nombre": "Enfermedad de Fabry"}]})

    monkeypatch.setattr(cdss.httpx, "put", fake_put)
    monkeypatch.setattr(cdss.httpx, "post", fake_post)

    result = CdssReal().sintomas_a_patologia(["247398009"], "menor_diferencia")

    assert result == ["FABRY"]
    method, url, kwargs = calls[0]
    assert (method, url) == ("PUT", "https://cdss.test/api/v1/configuracion/estrategia")
    assert kwargs["json"] == {"estrategia": "MENOR_DIFERENCIA"}
    assert kwargs["headers"] == {"X-API-Key": "clave-cdss"}
    method, url, kwargs = calls[1]
    assert (method, url) == ("POST", "https://cdss.test/api/v1/diagnostico")
    assert kwargs["json"] == {"sintomas": ["247398009"]}


def test_cdss_returns_every_tied_pathology(monkeypatch):
    monkeypatch.setattr(cdss.httpx, "put", lambda *a, **k: FakeResponse({}))
    monkeypatch.setattr(
        cdss.httpx,
        "post",
        lambda *a, **k: FakeResponse({"patologias": [{"codigo": "FABRY"}, {"codigo": "GAUCHER"}]}),
    )

    assert CdssReal().sintomas_a_patologia(["1"], "sintomas_coincidentes") == ["FABRY", "GAUCHER"]


def test_cdss_not_compatible_is_an_empty_list(monkeypatch):
    monkeypatch.setattr(cdss.httpx, "put", lambda *a, **k: FakeResponse({}))
    monkeypatch.setattr(
        cdss.httpx,
        "post",
        lambda *a, **k: FakeResponse({"compatible": False, "patologias": [], "mensaje": "no"}),
    )

    assert CdssReal().sintomas_a_patologia(["1"], "sintomas_coincidentes") == []


def test_cdss_with_an_error_status_raises(monkeypatch):
    monkeypatch.setattr(cdss.httpx, "put", lambda *a, **k: FakeResponse(status=401))

    with pytest.raises(httpx.HTTPStatusError):
        CdssReal().sintomas_a_patologia(["1"], "sintomas_coincidentes")


def test_apigen_asks_the_genes_of_a_pathology_by_its_code(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(["GAA"])

    monkeypatch.setattr(apigen.httpx, "post", fake_post)

    assert ApigenReal().genes_por_patologia("POMPE") == ["GAA"]
    url, kwargs = calls[0]
    assert url == "https://apigen.test/rest/v1/rpc/genes_por_patologia"
    assert kwargs["json"] == {"p_patologia": "POMPE"}
    assert kwargs["headers"] == {"apikey": "clave-apigen"}


def test_apigen_adds_the_secondary_findings_without_repeating(monkeypatch):
    monkeypatch.setattr(apigen.httpx, "post", lambda *a, **k: FakeResponse(["GAA"]))
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse([{"gen": "BRCA1"}, {"gen": "GAA"}])

    monkeypatch.setattr(apigen.httpx, "get", fake_get)

    genes = ApigenReal().genes_por_patologia("POMPE", con_hallazgos_secundarios=True)

    assert genes == ["GAA", "BRCA1"]
    assert calls[0][0] == "https://apigen.test/rest/v1/genes_hallazgos_secundarios"
    assert calls[0][1]["params"] == {"select": "gen"}


def test_apigen_does_not_ask_for_secondary_findings_unless_requested(monkeypatch):
    monkeypatch.setattr(apigen.httpx, "post", lambda *a, **k: FakeResponse(["GAA"]))

    def fail(*args, **kwargs):
        raise AssertionError("no tenía que pedir los hallazgos secundarios")

    monkeypatch.setattr(apigen.httpx, "get", fail)

    assert ApigenReal().genes_por_patologia("POMPE") == ["GAA"]


def test_apigen_searches_genes_by_prefix(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse([{"simbolo": "GAA"}, {"simbolo": "GAB1"}])

    monkeypatch.setattr(apigen.httpx, "get", fake_get)

    assert ApigenReal().buscar_genes("GA") == ["GAA", "GAB1"]
    url, kwargs = calls[0]
    assert url == "https://apigen.test/rest/v1/gen"
    assert kwargs["params"] == {"simbolo": "ilike.GA*", "select": "simbolo", "limit": 20}


def test_apigen_with_an_error_status_raises(monkeypatch):
    monkeypatch.setattr(apigen.httpx, "post", lambda *a, **k: FakeResponse(status=400))

    with pytest.raises(httpx.HTTPStatusError):
        ApigenReal().genes_por_patologia("XYZ")


def test_apigen_lists_its_pathologies_with_code_and_name(monkeypatch):
    rows = [
        {"codigo": "POMPE", "nombre": "Enfermedad de Pompe", "genes": ["GAA"], "de_grupo": False}
    ]
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeResponse(rows)

    monkeypatch.setattr(apigen.httpx, "post", fake_post)

    assert ApigenReal().listar_patologias() == [
        {"codigo": "POMPE", "nombre": "Enfermedad de Pompe"}
    ]
    assert calls == ["https://apigen.test/rest/v1/rpc/listar_patologias"]


PERSONAS = [{"parentesco": 0, "nombre": "Tomás", "apellido": "Ruiz"}]


def test_familiograma_lists_the_kinships_without_the_patient(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            [{"id": 0, "parentesco": "paciente"}, {"id": 1, "parentesco": "progenitor"}]
        )

    monkeypatch.setattr(familiograma.httpx, "get", fake_get)

    assert FamiliogramaReal().listar_parentescos() == [{"id": 1, "parentesco": "progenitor"}]
    url, kwargs = calls[0]
    assert url == "https://familiograma.test/v1/parentescos"
    assert kwargs["headers"] == {"x-api-key": "clave-familiograma"}


def test_familiograma_sends_the_people_and_returns_the_svg(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            {"advertencias": ["aviso"], "imagen": {"tipo": "image/svg+xml", "base64": "PHN2Zz4="}}
        )

    monkeypatch.setattr(familiograma.httpx, "post", fake_post)

    result = FamiliogramaReal().generar_familiograma(PERSONAS)

    assert result == {"advertencias": ["aviso"], "svg_base64": "PHN2Zz4="}
    url, kwargs = calls[0]
    assert url == "https://familiograma.test/v1"
    assert kwargs["json"] == {"personas": PERSONAS, "opciones": {"reglaSospecha": "desactivada"}}
    assert kwargs["headers"] == {"x-api-key": "clave-familiograma"}


def test_familiograma_turns_a_422_into_an_invalid_data_error(monkeypatch):
    error = {"error": {"codigo": "VALIDACION", "mensaje": "Vínculos ambiguos", "detalles": ["x"]}}
    monkeypatch.setattr(familiograma.httpx, "post", lambda *a, **k: FakeResponse(error, status=422))

    with pytest.raises(FamiliogramaInvalido) as raised:
        FamiliogramaReal().generar_familiograma(PERSONAS)

    assert raised.value.mensaje == "Vínculos ambiguos"
    assert raised.value.detalles == ["x"]


def test_familiograma_lets_the_other_errors_rise(monkeypatch):
    monkeypatch.setattr(familiograma.httpx, "post", lambda *a, **k: FakeResponse({}, status=502))

    with pytest.raises(httpx.HTTPStatusError):
        FamiliogramaReal().generar_familiograma(PERSONAS)


def test_familiograma_simulator_returns_kinships_and_a_svg():
    simulator = FamiliogramaSimulador()

    assert all(item["id"] != 0 for item in simulator.listar_parentescos())
    result = simulator.generar_familiograma(PERSONAS)
    assert result["advertencias"] == []
    assert base64.b64decode(result["svg_base64"]).startswith(b"<svg")
