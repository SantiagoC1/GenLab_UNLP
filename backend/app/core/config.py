from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ModoIntegracion = Literal["simulador", "real"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = ""
    session_expire_minutes: int = 30
    max_failed_attempts: int = 5
    code_expire_minutes: int = 10
    cors_origins: str = "http://localhost:5173"
    chatbot_url: str = "http://localhost:8001"
    # Solo desarrollo: acepta X-Dev-Role en lugar del login. Nunca activarlo fuera de la máquina
    # de quien desarrolla (ver app/core/dev_auth.py).
    dev_auth: bool = False

    # Un setting por integración: "simulador" o "real".
    integracion_familiograma: ModoIntegracion = "simulador"
    integracion_snomed: ModoIntegracion = "simulador"
    integracion_cupones: ModoIntegracion = "simulador"
    integracion_cdss: ModoIntegracion = "simulador"
    integracion_apigen: ModoIntegracion = "simulador"
    integracion_obras_sociales: ModoIntegracion = "simulador"
    integracion_avisos: ModoIntegracion = "simulador"
    integracion_optimizacion_recorrido: ModoIntegracion = "simulador"
    integracion_fedex: ModoIntegracion = "simulador"
    integracion_ministerio_salud: ModoIntegracion = "simulador"

    @property
    def cors_origins_lista(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
