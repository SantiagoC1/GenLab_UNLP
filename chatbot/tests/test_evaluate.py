import httpx
import pytest

from app.config import get_settings
from scripts import evaluate

REQUEST = httpx.Request("POST", "https://example.test/chat/completions")


def always_answers(_url, headers=None, json=None, timeout=None):
    """Un modelo malo: contesta todo como si fuera una consulta normal, sin respetar el alcance."""
    content = '{"tipo": "respuesta", "respuesta": "Texto del modelo sobre el exoma."}'
    body = {"choices": [{"message": {"content": content}}]}
    return httpx.Response(200, json=body, request=REQUEST)


def test_rules_mode_passes_every_critical_case_without_keys():
    results = evaluate.evaluate([evaluate.RULES], raw=False, delay=0)
    assert results and all(r.passed for r in results if r.case.critical)
    assert {r.provider for r in results} == {evaluate.RULES}


def test_the_battery_covers_every_required_category():
    categories = {case.category for case in evaluate._cases()}
    assert categories >= {
        "dentro de alcance",
        "fuera de alcance",
        "derivar al médico",
        "sin información",
        "continuación",
        "prompt injection",
        "datos personales",
    }


def test_conversations_are_isolated_between_consumers():
    assert evaluate.check_consumer_isolation() == (True, "")


def test_all_means_rules_plus_configured_providers(monkeypatch):
    assert evaluate.select_providers("all") == ["rules"]
    monkeypatch.setattr(get_settings(), "groq_api_key", "k")
    assert evaluate.select_providers("all") == ["rules", "groq"]
    assert evaluate.select_providers("groq") == ["groq"]
    with pytest.raises(SystemExit):
        evaluate.select_providers("nvidia")


def test_a_provider_that_ignores_the_rules_is_flagged_for_removal(monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", "k")
    monkeypatch.setattr(httpx, "post", always_answers)
    results = evaluate.evaluate(["groq"], raw=True, delay=0)
    failed = [r for r in results if r.case.critical and not r.passed]
    assert failed
    table = evaluate.to_markdown(results, (True, ""))
    assert "sacar de la cadena" in table


def test_raw_mode_never_sends_personal_data_to_the_model(monkeypatch):
    sent = []

    def recording(_url, headers=None, json=None, timeout=None):
        sent.append(json["messages"][-1]["content"])
        return always_answers(_url)

    monkeypatch.setattr(get_settings(), "groq_api_key", "k")
    monkeypatch.setattr(httpx, "post", recording)
    evaluate.evaluate(["groq"], raw=True, delay=0)
    assert not any(evaluate.EMAIL in text or evaluate.DNI in text for text in sent)


def test_report_files_are_written(tmp_path, capsys):
    prefix = tmp_path / "informe"
    code = evaluate.main_cli(["--provider", "rules", "--output", str(prefix)])
    assert code == 0
    assert "| Categoría |" in (tmp_path / "informe.md").read_text(encoding="utf-8")
    assert "pasa" in (tmp_path / "informe.csv").read_text(encoding="utf-8")
    assert "Resumen por proveedor" in capsys.readouterr().out
