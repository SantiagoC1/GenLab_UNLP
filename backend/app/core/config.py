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
    # Edge Function `chat` de Supabase. La apikey (publishable) y el token del grupo son secretos
    # del servidor: nunca van al frontend.
    chatbot_url: str = ""
    chatbot_apikey: str = ""
    chatbot_token: str = ""
    snomed_url: str = ""
    snomed_apikey: str = ""
    cdss_url: str = ""
    cdss_apikey: str = ""
    apigen_url: str = ""
    apigen_apikey: str = ""
    familiograma_url: str = ""
    familiograma_apikey: str = ""
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
    chatbot_integration: ModoIntegracion = "simulador"
    integracion_mercadopago: ModoIntegracion = "simulador"

    # Mercado Pago (Checkout Pro). El token es un secreto del servidor: nunca se escribe en el
    # código, ni en los logs, ni en el repositorio.
    mercadopago_access_token: str = ""
    # Moneda del cobro y cuántas unidades de esa moneda vale 1 USD (el presupuesto está en USD).
    mercadopago_currency_id: str = "ARS"
    mercadopago_usd_rate: float = 1.0
    # Máximo de cuotas que se ofrece en el checkout. Las cuotas las maneja Mercado Pago.
    mercadopago_max_installments: int = 6
    # A dónde vuelve el paciente desde Mercado Pago.
    frontend_url: str = "http://localhost:5173"

    @property
    def cors_origins_lista(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
