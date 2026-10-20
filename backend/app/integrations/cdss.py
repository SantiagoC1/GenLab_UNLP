"""Adaptador del módulo externo MA4."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de Cdss todavía no está cerrado (decisión 1 de la especificación)."


class CdssIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> str:
        """Devuelve: patología, o 'no compatible con patologías lisosomales'."""


class CdssSimulador(CdssIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> str:
        return "Fabry" if sintomas else "no compatible con patologías lisosomales"


class CdssReal(CdssIntegracion):
    """Cliente del módulo real."""

    def sintomas_a_patologia(self, sintomas: list[str], estrategia: str) -> str:
        raise NotImplementedError(_TODO)


def obtener_cdss() -> CdssIntegracion:
    if get_settings().integracion_cdss == "real":
        return CdssReal()
    return CdssSimulador()
