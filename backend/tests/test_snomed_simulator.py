import pytest

from app.integrations import snomed
from app.integrations.snomed import PAGE_SIZE, SnomedReal, SnomedSimulador


def search(text, page=1):
    return SnomedSimulador().buscar_terminos(text, page)


def test_the_result_has_the_agreed_shape():
    result = search("hipo")

    assert set(result) == {"items", "has_more"}
    assert result["items"], "el catálogo tiene términos con 'hipo'"
    assert all(set(item) == {"code", "term"} for item in result["items"])


def test_simulated_codes_are_not_taken_for_real_snomed_codes():
    assert all(item["code"].startswith("SIM-") for item in search("o")["items"])


@pytest.mark.parametrize("text", ["HIPOTONIA", "hipotonía", "hipotonia", "HiPoToNíA"])
def test_search_ignores_case_and_accents(text):
    assert [item["term"] for item in search(text)["items"]] == ["Hipotonía"]


def test_search_ignores_accents_written_as_combining_characters():
    assert [item["term"] for item in search("hipotoniá")["items"]] == ["Hipotonía"]


def test_without_matches_returns_an_empty_page():
    assert search("zzzz") == {"items": [], "has_more": False}


def test_results_come_in_the_same_order_every_time():
    assert search("o") == search("o")


def test_paginates_and_knows_when_there_is_one_more_page(monkeypatch):
    catalog = [{"code": f"SIM-{n:03}", "term": f"Síntoma {n}"} for n in range(PAGE_SIZE * 2)]
    monkeypatch.setattr(snomed, "_SIMULATED_CATALOG", catalog)

    first, second, third = search("sinto", 1), search("sinto", 2), search("sinto", 3)

    assert len(first["items"]) == PAGE_SIZE and first["has_more"] is True
    # el total es un múltiplo exacto del tamaño de página: la última página llena no promete otra
    assert len(second["items"]) == PAGE_SIZE and second["has_more"] is False
    assert third == {"items": [], "has_more": False}
    assert first["items"][0]["code"] != second["items"][0]["code"]


def test_the_real_client_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        SnomedReal().buscar_terminos("hipo")
