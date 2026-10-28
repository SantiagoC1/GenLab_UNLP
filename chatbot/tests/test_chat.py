import logging

from app import llm
from app.config import get_settings
from app.knowledge import load_knowledge
from app.scope import Kind


def ask(client, message, **extra):
    return client.post("/chat", json={"mensaje": message, **extra})


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_answers_from_the_knowledge_base(client):
    r = ask(client, "¿Qué es un exoma clínico?")
    body = r.json()
    assert r.status_code == 200
    assert body["tipo"] == "respuesta"
    assert "exoma" in body["respuesta"].lower()
    assert body["conversacion_id"]


def test_answers_about_each_lysosomal_pathology(client):
    for question, word in [
        ("¿Qué es la enfermedad de Fabry?", "alfa-galactosidasa"),
        ("¿Qué es Pompe?", "alfa-glucosidasa"),
        ("¿Qué es la MPS 1?", "iduronidasa"),
        ("Contame sobre Gaucher", "glucocerebrosidasa"),
        ("¿Qué es el ASMD?", "esfingomielinasa"),
    ]:
        body = ask(client, question).json()
        assert body["tipo"] == "respuesta", question
        assert word in body["respuesta"].lower(), question


def test_general_question_about_lysosomal_pathologies(client):
    body = ask(client, "¿Qué son las patologías lisosomales?").json()
    assert body["tipo"] == "respuesta"
    assert "lisosomas" in body["respuesta"].lower()


def test_explains_the_study_process(client):
    body = ask(client, "¿Cómo es el proceso del estudio?").json()
    assert body["tipo"] == "respuesta"
    assert "muestra de sangre" in body["respuesta"].lower()


def test_greeting_gets_an_introduction(client):
    body = ask(client, "Hola").json()
    assert body["tipo"] == "respuesta"
    assert "asistente" in body["respuesta"].lower()


def test_out_of_scope(client):
    body = ask(client, "¿Cómo va a estar el clima mañana?").json()
    assert body["tipo"] == "fuera_de_alcance"
    assert "estudios genéticos" in body["respuesta"]


def test_refers_to_the_doctor_instead_of_diagnosing(client):
    for question in [
        "¿Mi resultado quiere decir que estoy enfermo?",
        "Tengo Fabry, ¿qué tratamiento debo tomar?",
        "Me duele el pecho y tengo debilidad, ¿es lo que tengo?",
        "¿Qué medicamento me recomiendas?",
    ]:
        body = ask(client, question).json()
        assert body["tipo"] == "derivar_medico", question
        assert "médico tratante" in body["respuesta"]
        assert "laboratorio" not in body["respuesta"].lower().replace("estudios", "")


def test_says_when_it_has_no_information(client):
    body = ask(client, "¿Qué es la enfermedad de Danon?").json()
    assert body["tipo"] == "sin_informacion"
    assert "información suficiente" in body["respuesta"]


def test_keeps_the_conversation_id(client):
    first = ask(client, "¿Qué es un exoma?").json()["conversacion_id"]
    r = ask(client, "¿Y Pompe?", conversacion_id=first)
    assert r.json()["conversacion_id"] == first
    assert ask(client, "hola", conversacion_id="abc").json()["conversacion_id"] == "abc"


def test_rejects_empty_and_too_long_messages(client):
    assert ask(client, "").status_code == 422
    assert ask(client, "   ").status_code == 422
    assert ask(client, "a" * 1001).status_code == 422
    assert ask(client, "a" * 1000).status_code == 200


def test_unavailable_service_returns_503_with_message(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_available", False)
    for r in (client.get("/health"), ask(client, "hola")):
        assert r.status_code == 503
        assert "no está disponible" in r.json()["detail"]


def test_api_key_is_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_api_keys", "plataforma:clave1,grupo2:clave2")
    assert ask(client, "hola").status_code == 401
    assert (
        client.post("/chat", json={"mensaje": "hola"}, headers={"X-API-Key": "mala"}).status_code
        == 401
    )
    r = client.post("/chat", json={"mensaje": "hola"}, headers={"X-API-Key": "clave2"})
    assert r.status_code == 200


def test_rate_limit_per_consumer(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_rate_limit", 3)
    monkeypatch.setattr(get_settings(), "chatbot_api_keys", "a:ka,b:kb")
    for _ in range(3):
        assert (
            client.post("/chat", json={"mensaje": "hola"}, headers={"X-API-Key": "ka"}).status_code
            == 200
        )
    blocked = client.post("/chat", json={"mensaje": "hola"}, headers={"X-API-Key": "ka"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    # el límite es de cada consumidor
    assert (
        client.post("/chat", json={"mensaje": "hola"}, headers={"X-API-Key": "kb"}).status_code
        == 200
    )


def test_conversations_are_separated_by_consumer(client, monkeypatch):
    from app.main import store

    monkeypatch.setattr(get_settings(), "chatbot_api_keys", "a:ka,b:kb")
    client.post(
        "/chat",
        json={"mensaje": "¿Qué es un exoma?", "conversacion_id": "x"},
        headers={"X-API-Key": "ka"},
    )
    assert len(store.history("a", "x")) == 2
    assert store.history("b", "x") == []


def enable_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "clave-de-prueba")
    monkeypatch.setattr(get_settings(), "gemini_model", "modelo-de-prueba")


def test_uses_the_language_model_when_configured(client, monkeypatch):
    enable_model(monkeypatch)
    seen = {}

    def fake_generate(question, history, documents):
        seen["topics"] = [doc.topic for doc in documents]
        seen["history"] = history
        return llm.Reply(tipo=Kind.ANSWER, respuesta="Respuesta redactada por el modelo.")

    monkeypatch.setattr(llm, "generate", fake_generate)
    first = ask(client, "tengo una duda, ¿qué es un exoma?").json()
    assert first["respuesta"] == "Respuesta redactada por el modelo."
    assert first["tipo"] == "respuesta"
    # el modelo recibe toda la base, no solo los textos que coinciden por palabras
    assert len(seen["topics"]) == len(load_knowledge())
    ask(client, "¿y eso cómo se hereda?", conversacion_id=first["conversacion_id"])
    assert [turn["role"] for turn in seen["history"]] == ["user", "assistant"]


def test_the_model_decides_the_type_of_each_query(client, monkeypatch):
    enable_model(monkeypatch)
    for kind in Kind:
        monkeypatch.setattr(
            llm,
            "generate",
            lambda *_, kind=kind: llm.Reply(tipo=kind, respuesta="Texto del modelo."),
        )
        body = ask(client, "tengo una duda sobre Pompe").json()
        assert body["tipo"] == kind.value
        assert body["respuesta"] == "Texto del modelo."


def test_falls_back_to_the_rules_if_the_model_fails(client, monkeypatch):
    enable_model(monkeypatch)

    def failing(*_args):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(llm, "generate", failing)
    body = ask(client, "¿Qué es el exoma clínico?").json()
    assert body["tipo"] == "respuesta"
    assert "exoma" in body["respuesta"].lower()
    # el modelo caído no deja pasar un pedido de diagnóstico
    assert ask(client, "¿Qué medicamento me recomiendas?").json()["tipo"] == "derivar_medico"


def test_falls_back_to_the_rules_if_the_model_answers_garbage(client, monkeypatch):
    enable_model(monkeypatch)

    def garbage(*_args):
        return llm.Reply.model_validate_json("no es json")

    monkeypatch.setattr(llm, "generate", garbage)
    assert ask(client, "¿Qué es el exoma clínico?").json()["tipo"] == "respuesta"


def test_a_preamble_does_not_turn_a_general_question_into_a_referral(client):
    for question, word in [
        ("tengo una duda, ¿qué es un exoma?", "exoma"),
        ("Tengo una duda sobre Pompe", "alfa-glucosidasa"),
        ("Hola, tengo una consulta: ¿qué es la enfermedad de Fabry?", "alfa-galactosidasa"),
        ("Hola, ¿qué es un exoma?", "exoma"),
    ]:
        body = ask(client, question).json()
        assert body["tipo"] == "respuesta", question
        assert word in body["respuesta"].lower(), question


def test_a_personal_case_is_still_referred_to_the_doctor(client):
    assert ask(client, "Tengo Fabry, ¿qué hago?").json()["tipo"] == "derivar_medico"
    assert ask(client, "Tengo una duda: ¿tengo Fabry?").json()["tipo"] == "derivar_medico"


def test_thanks_and_greetings_are_not_out_of_scope(client):
    for message in ["gracias", "Muchas gracias!", "hola, ¿cómo estás?", "chau"]:
        assert ask(client, message).json()["tipo"] == "respuesta", message


def test_follow_up_uses_the_previous_question_without_the_model(client):
    first = ask(client, "¿Qué es la enfermedad de Fabry?").json()
    body = ask(client, "¿y cómo se hereda?", conversacion_id=first["conversacion_id"]).json()
    assert body["tipo"] == "respuesta"
    assert "x" in body["respuesta"].lower()
    # sin conversación previa no hay de qué colgarse
    assert ask(client, "¿y cómo se hereda?").json()["tipo"] != "respuesta"


def test_logs_queries_without_personal_data(client, caplog):
    with caplog.at_level(logging.INFO, logger="chatbot.consultas"):
        ask(client, "Mi mail es ana@ejemplo.com y mi DNI 12345678, ¿qué es un exoma?")
    logged = caplog.text
    assert "[mail]" in logged and "[número]" in logged
    assert "ana@ejemplo.com" not in logged and "12345678" not in logged


def test_openapi_visible(client):
    assert client.get("/docs").status_code == 200
    assert "/chat" in client.get("/openapi.json").json()["paths"]


def test_every_mention_of_treatment_is_referred_to_the_doctor(client):
    for question in [
        "¿Qué tratamiento existe para Fabry?",
        "¿Se puede tratar Pompe?",
        "¿Tiene cura el Gaucher?",
        "¿Qué terapias hay para la MPS 1?",
        "tengo una duda: ¿qué medicamento se usa en el ASMD?",
    ]:
        body = ask(client, question).json()
        assert body["tipo"] == "derivar_medico", question
