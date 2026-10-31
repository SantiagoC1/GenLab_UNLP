import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.conversations import ConversationStore
from app.main import app
from app.providers import cooldown
from app.ratelimit import RateLimiter


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    """Cada test arranca sin clave de modelo, sin claves de consumidores y con memoria limpia."""
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "chatbot_llm_providers", "gemini,groq,nvidia")
    cooldown.reset()
    monkeypatch.setattr(settings, "chatbot_api_keys", "")
    monkeypatch.setattr(settings, "chatbot_available", True)
    monkeypatch.setattr("app.main.store", ConversationStore())
    monkeypatch.setattr("app.main.limiter", RateLimiter())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
