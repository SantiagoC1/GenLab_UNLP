from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

CHATBOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = CHATBOT_DIR / "knowledge"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # El .env de la raíz del repo y, si existe, uno propio del chatbot
        env_file=(CHATBOT_DIR.parent / ".env", CHATBOT_DIR / ".env"),
        extra="ignore",
    )
    # La clave y el modelo de Gemini se leen solo del entorno. Nunca van en el código.
    gemini_api_key: str = ""
    gemini_model: str = ""
    # Si es False, o falta la clave, responde con el texto de la base de conocimiento sin modelo.
    chatbot_use_llm: bool = True
    # Permite apagar el servicio (por ejemplo, en mantenimiento): /health y /chat responden 503.
    chatbot_available: bool = True
    cors_origins: str = "*"
    # Claves de los consumidores, con el formato "nombre:clave,nombre:clave" (decisión 7 pendiente).
    # Si está vacío no se pide clave: solo para desarrollo.
    chatbot_api_keys: str = ""
    # Consultas por minuto de cada consumidor (M11-RF9).
    chatbot_rate_limit: int = 20
    # Minutos sin mensajes después de los cuales se olvida una conversación (M11-RF6).
    conversation_ttl_minutes: int = 30
    # Cantidad de mensajes anteriores que se le pasan al modelo.
    conversation_max_turns: int = 6

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def consumers(self):
        """Devuelve {clave: nombre del consumidor} a partir de CHATBOT_API_KEYS."""
        result = {}
        for item in self.chatbot_api_keys.split(","):
            name, _, key = item.strip().partition(":")
            if name and key:
                result[key.strip()] = name.strip()
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
