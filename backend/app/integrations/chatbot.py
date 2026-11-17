"""Adaptador del chatbot (M11), que corre como Edge Function en Supabase."""

import uuid
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings
from app.core.errors import InvalidIntegration, TooManyRequests

TIMEOUT_SECONDS = 20
_NAME = "chatbot"


class ChatbotIntegration(ABC):
    """Interfaz que usa el resto del sistema.

    El contrato real puede cambiar sin tocar a los demás.
    """

    @abstractmethod
    def ask(self, message: str, conversation_id: str | None):
        """Devuelve answer, conversation_id y kind.

        kind es respuesta, fuera_de_alcance, derivar_medico o
        sin_informacion, los valores del contrato del chatbot.
        """


class ChatbotSimulator(ChatbotIntegration):
    """Responde con un texto de ejemplo, sin depender de Supabase."""

    def ask(self, message: str, conversation_id: str | None):
        return {
            "answer": "Esta es una respuesta de ejemplo del chatbot (simulador).",
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "kind": "respuesta",
        }


class ChatbotReal(ChatbotIntegration):
    """Cliente de la Edge Function `chat`."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def ask(self, message: str, conversation_id: str | None):
        settings = get_settings()
        if not (settings.chatbot_url and settings.chatbot_apikey and settings.chatbot_token):
            raise InvalidIntegration(_NAME)

        headers = {"apikey": settings.chatbot_apikey, "x-chatbot-token": settings.chatbot_token}
        body = {"mensaje": message, "conversacion_id": conversation_id}
        try:
            if self._client is not None:
                response = self._client.post(settings.chatbot_url, headers=headers, json=body)
            else:
                response = httpx.post(
                    settings.chatbot_url, headers=headers, json=body, timeout=TIMEOUT_SECONDS
                )
        except httpx.HTTPError as error:
            raise InvalidIntegration(_NAME) from error

        if response.status_code == 429:
            raise TooManyRequests(
                "Hay muchas consultas en este momento. Probá de nuevo en unos segundos."
            )
        if response.status_code != 200:
            raise InvalidIntegration(_NAME)

        data = response.json()
        return {
            "answer": data["respuesta"],
            "conversation_id": data["conversacion_id"],
            "kind": data["tipo"],
        }


def get_chatbot() -> ChatbotIntegration:
    if get_settings().chatbot_integration == "real":
        return ChatbotReal()
    return ChatbotSimulator()
