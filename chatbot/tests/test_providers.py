import json
import logging

import httpx
import pytest

from app import providers
from app.config import get_settings
from app.knowledge import load_knowledge
from app.prompt import Reply
from app.providers import (
    GeminiProvider,
    NoProviderAvailable,
    ProviderError,
    cooldown,
    generate_with_fallback,
    parse_reply,
    provider_chain,
)
from app.scope import Kind

REQUEST = httpx.Request("POST", "https://example.test/chat/completions")


def ask(client, message, **extra):
    return client.post("/chat", json={"mensaje": message, **extra})


def completion(content: str, status: int = 200, headers: dict | None = None) -> httpx.Response:
    body = {"choices": [{"message": {"role": "assistant", "content": content}}]}
    return httpx.Response(status, json=body, headers=headers, request=REQUEST)


def model_json(text="Respuesta del modelo.", kind="respuesta") -> str:
    return json.dumps({"tipo": kind, "respuesta": text})


@pytest.fixture
def keys(monkeypatch):
    """Deja configurados Gemini, Groq y NVIDIA."""
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "k-gemini")
    monkeypatch.setattr(settings, "gemini_model", "m-gemini")
    monkeypatch.setattr(settings, "groq_api_key", "k-groq")
    monkeypatch.setattr(settings, "nvidia_api_key", "k-nvidia")


@pytest.fixture
def gemini(monkeypatch):
    """Controla qué hace Gemini: `gemini.behavior` es una función o una excepción."""

    class Control:
        calls = 0
        behavior = staticmethod(lambda: Reply(tipo=Kind.ANSWER, respuesta="Respuesta de Gemini."))

    def fake_generate(self, question, history, documents):
        Control.calls += 1
        result = Control.behavior()
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(GeminiProvider, "generate", fake_generate)
    return Control


@pytest.fixture
def http(monkeypatch):
    """Reemplaza `httpx.post`: `http.queue` tiene respuestas o excepciones, una por llamada."""

    class Control:
        queue: list = []
        sent: list = []

    def fake_post(url, headers=None, json=None, timeout=None):
        Control.sent.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        item = Control.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    Control.queue, Control.sent = [], []
    monkeypatch.setattr(httpx, "post", fake_post)
    return Control


def quota_error(name="gemini", retry_after=None):
    return ProviderError(name, "quota", "HTTP 429", retry_after)


def test_gemini_fails_and_groq_answers(client, keys, gemini, http, caplog):
    gemini.behavior = lambda: quota_error()
    http.queue = [completion(model_json("Respuesta de Groq."))]
    with caplog.at_level(logging.INFO, logger="chatbot.consultas"):
        body = ask(client, "¿Qué es un exoma?").json()
    assert body["respuesta"] == "Respuesta de Groq."
    assert body["tipo"] == "respuesta"
    assert '"provider": "groq"' in caplog.text


def test_falls_through_the_whole_chain_to_nvidia(client, keys, gemini, http):
    gemini.behavior = lambda: ProviderError("gemini", "unavailable", "timeout")
    http.queue = [completion("", status=500), completion(model_json("Respuesta de NVIDIA."))]
    body = ask(client, "¿Qué es un exoma?").json()
    assert body["respuesta"] == "Respuesta de NVIDIA."
    assert [call["url"] for call in http.sent] == [
        "https://api.groq.com/openai/v1/chat/completions",
        "https://integrate.api.nvidia.com/v1/chat/completions",
    ]


def test_falls_back_to_rules_when_all_providers_fail(client, keys, gemini, http, caplog):
    gemini.behavior = lambda: RuntimeError("boom")
    http.queue = [httpx.ConnectTimeout("lento"), completion("", status=503)]
    with caplog.at_level(logging.INFO, logger="chatbot.consultas"):
        body = ask(client, "¿Qué es el exoma clínico?").json()
    assert body["tipo"] == "respuesta"
    assert "exoma" in body["respuesta"].lower()
    assert '"provider": "rules"' in caplog.text
    # y las reglas siguen derivando al médico
    assert ask(client, "¿Qué medicamento me recomiendas?").json()["tipo"] == "derivar_medico"


def test_a_429_starts_the_cooldown_and_the_next_query_skips_the_provider(
    client, keys, gemini, http
):
    gemini.behavior = lambda: quota_error()
    http.queue = [completion(model_json("Uno.")), completion(model_json("Dos."))]
    assert ask(client, "¿Qué es un exoma?").json()["respuesta"] == "Uno."
    assert gemini.calls == 1 and cooldown.is_down("gemini")
    assert ask(client, "¿Qué es Pompe?").json()["respuesta"] == "Dos."
    assert gemini.calls == 1  # no se volvió a intentar


def test_http_429_from_an_openai_compatible_provider_starts_the_cooldown(keys, http, gemini):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [
        completion("", status=429, headers={"retry-after": "30"}),
        completion(model_json("De NVIDIA.")),
    ]
    reply = generate_with_fallback("hola", [], list(load_knowledge()))
    assert reply.provider == "nvidia"
    assert cooldown.is_down("groq")


def test_cooldown_uses_retry_after_and_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(providers.time, "monotonic", lambda: now[0])
    cooldown.mark_down("groq", 30)
    assert cooldown.is_down("groq")
    now[0] += 29
    assert cooldown.is_down("groq")
    now[0] += 2
    assert not cooldown.is_down("groq")


def test_cooldown_default_comes_from_the_settings(keys, gemini, http, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_provider_cooldown_seconds", 5)
    gemini.behavior = lambda: quota_error()
    http.queue = [completion(model_json())]
    generate_with_fallback("hola", [], list(load_knowledge()))
    now = providers.time.monotonic()
    monkeypatch.setattr(providers.time, "monotonic", lambda: now + 6)
    assert not cooldown.is_down("gemini")


def test_invalid_json_moves_on_without_cooldown(keys, gemini, http):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [completion("esto no es json"), completion(model_json("Válida."))]
    reply = generate_with_fallback("hola", [], list(load_knowledge()))
    assert reply.provider == "nvidia" and reply.respuesta == "Válida."
    assert not cooldown.is_down("groq")


def test_a_wrong_type_value_counts_as_invalid(keys, gemini, http):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [completion(model_json(kind="inventado")), completion(model_json("Válida."))]
    assert generate_with_fallback("hola", [], list(load_knowledge())).provider == "nvidia"


def test_all_providers_cooling_down_raises_without_calling_anyone(keys, gemini, http):
    for name in ("gemini", "groq", "nvidia"):
        cooldown.mark_down(name, 60)
    with pytest.raises(NoProviderAvailable):
        generate_with_fallback("hola", [], list(load_knowledge()))
    assert gemini.calls == 0 and http.sent == []


def test_providers_without_a_key_are_skipped(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "nvidia_api_key", "k-nvidia")
    assert [p.name for p in provider_chain()] == ["nvidia"]
    # Gemini necesita clave y modelo
    monkeypatch.setattr(settings, "gemini_api_key", "k-gemini")
    assert [p.name for p in provider_chain()] == ["nvidia"]
    monkeypatch.setattr(settings, "gemini_model", "m-gemini")
    assert [p.name for p in provider_chain()] == ["gemini", "nvidia"]


def test_the_order_of_the_chain_is_configurable(keys, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_llm_providers", "nvidia, groq")
    assert [p.name for p in provider_chain()] == ["nvidia", "groq"]


def test_unknown_and_repeated_names_are_ignored(keys, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_llm_providers", "groq,otro,groq")
    assert [p.name for p in provider_chain()] == ["groq"]


def test_openrouter_is_optional_and_needs_a_model(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "chatbot_llm_providers", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "k-or")
    assert provider_chain() == []
    monkeypatch.setattr(settings, "openrouter_model", "algun/modelo:free")
    assert [p.name for p in provider_chain()] == ["openrouter"]


def test_the_chain_can_be_turned_off(client, keys, gemini, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_use_llm", False)
    ask(client, "¿Qué es un exoma?")
    assert gemini.calls == 0


def test_openai_request_maps_roles_and_json_mode(keys, gemini, http):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [completion(model_json())]
    history = [
        {"role": "user", "content": "¿Qué es Fabry?"},
        {"role": "assistant", "content": "Es una enfermedad lisosomal."},
    ]
    generate_with_fallback("¿y cómo se hereda?", history, list(load_knowledge()))
    sent = http.sent[0]
    assert sent["headers"] == {"Authorization": "Bearer k-groq"}
    assert sent["timeout"] == get_settings().chatbot_llm_timeout_seconds
    payload = sent["json"]
    assert payload["model"] == "openai/gpt-oss-120b"
    assert payload["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in payload["messages"]] == ["system", "user", "assistant", "user"]
    assert "DOCUMENTOS" in payload["messages"][0]["content"]
    assert payload["messages"][-1]["content"] == "¿y cómo se hereda?"


def test_nvidia_asks_for_json_in_the_prompt_instead_of_response_format(keys, gemini, http):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [completion("", status=500), completion(model_json())]
    generate_with_fallback("hola", [], list(load_knowledge()))
    nvidia_payload = http.sent[1]["json"]
    assert "response_format" not in nvidia_payload
    assert "objeto JSON" in nvidia_payload["messages"][0]["content"]


def test_unexpected_response_shape_is_invalid(keys, gemini, http):
    gemini.behavior = lambda: RuntimeError("fuera")
    http.queue = [
        httpx.Response(200, json={"error": "raro"}, request=REQUEST),
        completion(model_json("Válida.")),
    ]
    assert generate_with_fallback("hola", [], list(load_knowledge())).provider == "nvidia"


@pytest.mark.parametrize(
    "text",
    [
        '{"tipo": "respuesta", "respuesta": "Hola"}',
        '```json\n{"tipo": "respuesta", "respuesta": "Hola"}\n```',
        'Claro, acá va: {"tipo": "respuesta", "respuesta": "Hola"} Espero que sirva.',
    ],
)
def test_parse_reply_tolerates_code_fences_and_surrounding_text(text):
    reply = parse_reply("groq", text)
    assert reply.respuesta == "Hola" and reply.tipo == Kind.ANSWER


def test_parse_reply_rejects_garbage():
    with pytest.raises(ProviderError) as error:
        parse_reply("groq", "no hay json acá")
    assert error.value.kind == "invalid"
