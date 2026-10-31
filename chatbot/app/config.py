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
    # Si es False, o no hay ningún proveedor con clave, responde con el texto de la base sin modelo.
    chatbot_use_llm: bool = True
    # Orden de la cadena de proveedores de IA. Los que no tienen clave se saltean solos.
    chatbot_llm_providers: str = "gemini,groq,nvidia"
    # Tiempo máximo de espera de cada proveedor antes de pasar al siguiente.
    chatbot_llm_timeout_seconds: float = 12
    # Cuánto se saltea un proveedor después de agotar su cuota o caerse.
    chatbot_provider_cooldown_seconds: int = 90
    # Groq, NVIDIA NIM y OpenRouter hablan el formato de OpenAI. Todos tienen plan gratuito.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    nvidia_api_key: str = ""
    nvidia_model: str = "openai/gpt-oss-120b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    # OpenRouter es opcional y no trae modelo por defecto: los gratuitos cambian seguido.
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Caché de respuestas a consultas repetidas (solo primer mensaje de una conversación).
    chatbot_cache_ttl_minutes: int = 60
    chatbot_cache_max_entries: int = 500
    # Si la base tiene más de este número de textos, al modelo se le pasan solo los más parecidos.
    chatbot_prompt_max_documents: int = 12
    chatbot_prompt_top_documents: int = 3
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
    def llm_providers_list(self) -> list[str]:
        names = (name.strip().lower() for name in self.chatbot_llm_providers.split(","))
        return [name for name in names if name]

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
