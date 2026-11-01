import json

import httpx
import pytest

from app.core.config import get_settings
from app.core.enums import Rol
from app.core.errors import InvalidIntegration, TooManyRequests
from app.integrations.chatbot import (
    ChatbotIntegration,
    ChatbotReal,
    ChatbotSimulator,
    get_chatbot,
)
from app.main import app


def test_simulator_is_the_default_mode():
    assert isinstance(get_chatbot(), ChatbotSimulator)


def test_real_mode_returns_the_real_client(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_integration", "real")
    assert isinstance(get_chatbot(), ChatbotReal)


def test_simulator_keeps_the_conversation_id():
    simulator = ChatbotSimulator()
    assert simulator.ask("Hola", "c-5")["conversation_id"] == "c-5"
    assert simulator.ask("Hola", None)["conversation_id"]


class ChatbotSpy(ChatbotIntegration):
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    def ask(self, message, conversation_id):
        self.calls.append((message, conversation_id))
        if self.error:
            raise self.error
        return {
            "answer": "Hola",
            "conversation_id": conversation_id or "c-1",
            "kind": "respuesta",
        }


@pytest.fixture
def chatbot():
    spy = ChatbotSpy()
    app.dependency_overrides[get_chatbot] = lambda: spy
    return spy


def test_patient_asks_and_gets_the_answer(client, login_as, chatbot):
    login_as(Rol.PACIENTE)
    response = client.post("/chatbot/messages", json={"message": "  ¿Qué es un exoma?  "})
    assert response.status_code == 200
    assert response.json() == {"answer": "Hola", "conversation_id": "c-1", "kind": "respuesta"}
    assert chatbot.calls == [("¿Qué es un exoma?", None)]


def test_conversation_id_is_forwarded(client, login_as, chatbot):
    login_as(Rol.PACIENTE)
    response = client.post(
        "/chatbot/messages", json={"message": "¿y cómo se hereda?", "conversation_id": "c-9"}
    )
    assert response.json()["conversation_id"] == "c-9"
    assert chatbot.calls == [("¿y cómo se hereda?", "c-9")]


@pytest.mark.parametrize("role", [Rol.MEDICO_TRATANTE, Rol.ADMINISTRADOR_GENERAL])
def test_only_the_patient_can_ask(client, login_as, chatbot, role):
    login_as(role)
    response = client.post("/chatbot/messages", json={"message": "Hola"})
    assert response.status_code == 403
    assert chatbot.calls == []


def test_asking_without_a_session_is_rejected(client, chatbot):
    response = client.post("/chatbot/messages", json={"message": "Hola"})
    assert response.status_code == 401
    assert chatbot.calls == []


@pytest.mark.parametrize(
    "body, expected_text",
    [
        ({}, "'mensaje' es obligatorio"),
        ({"message": "   "}, "'mensaje' es obligatorio"),
        ({"message": "a" * 1001}, "más de 1000 caracteres"),
        ({"message": "Hola", "conversation_id": "x" * 201}, "conversación no es válido"),
    ],
)
def test_invalid_message_is_rejected(client, login_as, chatbot, body, expected_text):
    login_as(Rol.PACIENTE)
    response = client.post("/chatbot/messages", json=body)
    assert response.status_code == 422
    assert expected_text in response.json()["detalle"]
    assert chatbot.calls == []


def test_message_of_exactly_1000_characters_is_accepted(client, login_as, chatbot):
    login_as(Rol.PACIENTE)
    response = client.post("/chatbot/messages", json={"message": "a" * 1000})
    assert response.status_code == 200


def test_unavailable_chatbot_responds_503(client, login_as):
    spy = ChatbotSpy(InvalidIntegration("chatbot"))
    app.dependency_overrides[get_chatbot] = lambda: spy
    login_as(Rol.PACIENTE)
    response = client.post("/chatbot/messages", json={"message": "Hola"})
    assert response.status_code == 503
    assert "chatbot" in response.json()["detalle"]


def test_too_many_requests_responds_429(client, login_as):
    spy = ChatbotSpy(TooManyRequests("Probá de nuevo en unos segundos."))
    app.dependency_overrides[get_chatbot] = lambda: spy
    login_as(Rol.PACIENTE)
    response = client.post("/chatbot/messages", json={"message": "Hola"})
    assert response.status_code == 429


# --- Cliente real, con un servidor simulado en lugar de Supabase ---


@pytest.fixture
def credentials(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "chatbot_url", "https://ref.supabase.co/functions/v1/chat")
    monkeypatch.setattr(settings, "chatbot_apikey", "sb_publishable_x")
    monkeypatch.setattr(settings, "chatbot_token", "token-del-grupo")


def real_client(handler) -> ChatbotReal:
    return ChatbotReal(httpx.Client(transport=httpx.MockTransport(handler)))


def test_real_client_sends_the_headers_and_the_body(credentials):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"respuesta": "Hola", "conversacion_id": "c-1", "tipo": "respuesta"}
        )

    result = real_client(handler).ask("¿Qué es un exoma?", None)

    assert result == {"answer": "Hola", "conversation_id": "c-1", "kind": "respuesta"}
    (request,) = requests
    assert str(request.url) == "https://ref.supabase.co/functions/v1/chat"
    assert request.headers["apikey"] == "sb_publishable_x"
    assert request.headers["x-chatbot-token"] == "token-del-grupo"
    assert json.loads(request.read()) == {"mensaje": "¿Qué es un exoma?", "conversacion_id": None}


def test_real_client_translates_429(credentials):
    with pytest.raises(TooManyRequests):
        real_client(lambda r: httpx.Response(429, json={"detail": "x"})).ask("Hola", None)


@pytest.mark.parametrize("status", [401, 422, 500, 503])
def test_real_client_translates_failures_to_unavailable(credentials, status):
    with pytest.raises(InvalidIntegration):
        real_client(lambda r: httpx.Response(status, json={"detail": "x"})).ask("Hola", None)


def test_real_client_translates_timeout(credentials):
    def handler(request):
        raise httpx.ConnectTimeout("sin respuesta")

    with pytest.raises(InvalidIntegration):
        real_client(handler).ask("Hola", None)


def test_real_client_rejects_an_unexpected_response(credentials):
    with pytest.raises(InvalidIntegration):
        real_client(lambda r: httpx.Response(200, json={"otra": "cosa"})).ask("Hola", None)


def test_real_client_fails_when_credentials_are_missing(monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_url", "")
    with pytest.raises(InvalidIntegration):
        real_client(lambda r: httpx.Response(200, json={})).ask("Hola", None)
