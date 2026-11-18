"""Adaptador del CDSS, el módulo externo que sugiere la patología."""

from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

TIMEOUT_SECONDS = 15
_STRATEGIES = {
    "sintomas_coincidentes": "MAYOR_CANTIDAD_SINTOMAS",
    "sintomas_cardinales_coincidentes": "MAYOR_CANTIDAD_CARDINALES",
    "menor_diferencia": "MENOR_DIFERENCIA",
}


class CdssIntegracion(ABC):
    """Interfaz que usa el resto del sistema.

    El contrato real puede cambiar sin tocar a los demás.
    """

    @abstractmethod
    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> list[str]:
        """Devuelve los códigos de las patologías sugeridas.

        Pueden ser varias si empatan. La lista vacía significa "no
        compatible con patologías lisosomales".
        """


class CdssSimulador(CdssIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> list[str]:
        return ["FABRY"] if sintomas else []


class CdssReal(CdssIntegracion):
    """Cliente del CDSS del otro grupo."""

    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> list[str]:
        """Fija la estrategia y pide la sugerencia al CDSS real.

        La estrategia es una sola por grupo, así que se fija antes de
        cada consulta.
        """
        settings = get_settings()
        base = settings.cdss_url.rstrip("/")
        headers = {"X-API-Key": settings.cdss_apikey}

        response = httpx.put(
            f"{base}/configuracion/estrategia",
            json={"estrategia": _STRATEGIES[estrategia]},
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        response = httpx.post(
            f"{base}/diagnostico",
            json={"sintomas": sintomas},
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [pathology["codigo"] for pathology in response.json()["patologias"]]


def obtener_cdss() -> CdssIntegracion:
    if get_settings().integracion_cdss == "real":
        return CdssReal()
    return CdssSimulador()
