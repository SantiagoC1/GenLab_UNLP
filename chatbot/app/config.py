from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # La clave de la API de Anthropic se lee solo del entorno. Nunca va en el código.
    anthropic_api_key: str = ""
    # Permite apagar el servicio (por ejemplo, en mantenimiento): /health y /chat responden 503.
    chatbot_disponible: bool = True
    cors_origins: str = "*"

    @property
    def cors_origins_lista(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
