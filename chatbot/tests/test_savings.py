import logging

import pytest

from app import llm
from app.cache import ResponseCache, cache_key
from app.config import get_settings
from app.knowledge import best_fragment, load_knowledge, select_for_prompt
from app.scope import Kind


def ask(client, message, **extra):
    return client.post("/chat", json={"mensaje": message, **extra})


def doc(topic):
    return next(d for d in load_knowledge() if d.topic == topic)


@pytest.fixture
def model(monkeypatch):
    """Activa el modelo y cuenta las llamadas. `model.kind` y `model.text` fijan la respuesta."""
    monkeypatch.setattr(get_settings(), "gemini_api_key", "clave-de-prueba")
    monkeypatch.setattr(get_settings(), "gemini_model", "modelo-de-prueba")

    class Control:
        calls: list = []
        kind = Kind.ANSWER
        text = "Respuesta del modelo."

    def fake_generate(question, history, documents):
        Control.calls.append((question, history, documents))
        return llm.Reply(tipo=Control.kind, respuesta=Control.text).with_provider("gemini")

    Control.calls = []
    monkeypatch.setattr(llm, "generate", fake_generate)
    return Control


# --- Atajo sin modelo ---


@pytest.mark.parametrize(
    ("message", "kind"),
    [
        ("Hola", "respuesta"),
        ("Muchas gracias!", "respuesta"),
        ("¿Qué medicamento me recomiendas?", "derivar_medico"),
        ("Tengo Fabry, ¿qué hago?", "derivar_medico"),
    ],
)
def test_trivial_messages_do_not_use_the_model(client, model, caplog, message, kind):
    with caplog.at_level(logging.INFO, logger="chatbot.consultas"):
        body = ask(client, message).json()
    assert body["tipo"] == kind
    assert model.calls == []
    assert '"provider": "rules"' in caplog.text


# --- Caché ---


def test_cache_key_ignores_case_accents_signs_and_spaces():
    assert cache_key("  ¿Qué   es el EXOMA clínico?! ") == cache_key("que es el exoma clinico")


def test_repeated_questions_come_from_the_cache(client, model, caplog):
    first = ask(client, "¿Qué es un exoma?").json()
    with caplog.at_level(logging.INFO, logger="chatbot.consultas"):
        second = ask(client, "que es un EXOMA").json()
    assert len(model.calls) == 1
    assert second["respuesta"] == first["respuesta"] == "Respuesta del modelo."
    assert '"provider": "cache"' in caplog.text
    # cada paciente conserva su propia conversación
    assert second["conversacion_id"] != first["conversacion_id"]


def test_questions_with_history_skip_the_cache(client, model):
    first = ask(client, "¿Qué es un exoma?").json()
    ask(client, "¿Qué es un exoma?", conversacion_id=first["conversacion_id"])
    assert len(model.calls) == 2


def test_questions_with_masked_personal_data_are_not_cached(client, model):
    for _ in range(2):
        ask(client, "Mi DNI es 12345678, ¿qué es un exoma?")
    assert len(model.calls) == 2


def test_referrals_from_the_model_are_not_cached(client, model):
    model.kind = Kind.REFER_TO_DOCTOR
    for _ in range(2):
        ask(client, "Me quedé pensando en mi familia y en Pompe")
    assert len(model.calls) == 2


def test_the_cache_only_stores_what_the_model_answered(client):
    # sin modelo la respuesta sale de las reglas y no se guarda
    from app.main import cache

    ask(client, "¿Qué es un exoma?")
    assert cache.get("¿Qué es un exoma?") is None


def test_cache_entries_expire(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.cache.time.monotonic", lambda: now[0])
    monkeypatch.setattr(get_settings(), "chatbot_cache_ttl_minutes", 1)
    store = ResponseCache()
    store.put("¿Qué es Pompe?", "texto", Kind.ANSWER)
    now[0] += 59
    assert store.get("qué es pompe").text == "texto"
    now[0] += 2
    assert store.get("qué es pompe") is None


def test_cache_keeps_a_maximum_of_entries(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_cache_max_entries", 2)
    store = ResponseCache()
    for name in ("uno", "dos", "tres"):
        store.put(name, name, Kind.ANSWER)
    assert store.get("uno") is None
    assert store.get("dos") and store.get("tres")


# --- Prompt más chico ---


def test_a_small_base_goes_whole_to_the_model():
    documents = load_knowledge()
    assert select_for_prompt("¿Qué es Pompe?", [], documents) == list(documents)


def test_a_big_base_sends_only_the_closest_texts(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_prompt_max_documents", 5)
    monkeypatch.setattr(get_settings(), "chatbot_prompt_top_documents", 2)
    selected = select_for_prompt("¿Qué es Pompe?", [], load_knowledge())
    assert 1 <= len(selected) <= 2
    assert selected[0].topic == "Enfermedad de Pompe"


def test_a_big_base_sends_everything_if_nothing_matches(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_prompt_max_documents", 5)
    documents = load_knowledge()
    assert select_for_prompt("receta de empanadas", [], documents) == list(documents)


def test_a_follow_up_is_matched_with_the_previous_question(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_prompt_max_documents", 5)
    history = [{"role": "user", "content": "¿Qué es Pompe?"}, {"role": "assistant", "content": "x"}]
    selected = select_for_prompt("¿y cómo se hereda?", history, load_knowledge())
    assert selected[0].topic == "Enfermedad de Pompe"


# --- Modo reglas con respuestas más cortas ---


def test_rules_answer_a_specific_question_with_the_matching_part(client):
    body = ask(client, "¿Qué es una VUS?").json()["respuesta"]
    assert "significado incierto" in body
    assert "Benigna" not in body and "Patogénica" not in body
    assert "médico tratante" in body


def test_rules_answer_how_it_is_inherited_without_the_rest(client):
    body = ask(client, "¿Cómo se hereda Pompe?").json()["respuesta"]
    assert "autosómica recesiva" in body
    assert "forma infantil" not in body
    assert "médico tratante" in body


def test_rules_give_the_whole_text_when_the_question_only_names_the_topic(client):
    body = ask(client, "¿Qué es Pompe?").json()["respuesta"]
    assert "alfa-glucosidasa" in body and "autosómica" in body and "forma infantil" in body


def test_rules_give_the_whole_process_for_a_general_question(client):
    body = ask(client, "¿Cómo es el proceso del estudio?").json()["respuesta"]
    assert "1. " in body and "6. " in body and "reanálisis" in body


def test_best_fragment_always_keeps_the_closing_sentence():
    fabry = doc("Enfermedad de Fabry")
    fragment = best_fragment("¿qué órganos compromete?", fabry)
    assert fragment.endswith("Consultá a tu médico tratante.")
    assert len(fragment) < len(fabry.body)
