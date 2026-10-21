import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import RESPUESTA_FIJA, app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_chat_responde_texto_fijo_y_crea_conversacion(client):
    r = client.post("/chat", json={"mensaje": "¿Qué es un exoma?", "conversacion_id": None})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["respuesta"] == RESPUESTA_FIJA
    assert cuerpo["conversacion_id"]


def test_chat_conserva_el_id_de_conversacion(client):
    r = client.post("/chat", json={"mensaje": "hola", "conversacion_id": "abc"})
    assert r.json()["conversacion_id"] == "abc"


def test_chat_rechaza_mensaje_vacio(client):
    assert client.post("/chat", json={"mensaje": ""}).status_code == 422


def test_servicio_no_disponible_devuelve_503_con_mensaje(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "chatbot_disponible", False)
    for r in (client.get("/health"), client.post("/chat", json={"mensaje": "hola"})):
        assert r.status_code == 503
        assert "no está disponible" in r.json()["detail"]


def test_openapi_visible(client):
    assert client.get("/docs").status_code == 200
    assert "/chat" in client.get("/openapi.json").json()["paths"]
