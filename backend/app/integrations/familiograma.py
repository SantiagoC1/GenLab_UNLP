"""Adaptador del módulo externo MA1."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de Familiograma todavía no está cerrado (decisión 1 de la especificación)."


class FamiliogramaIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def generar_familiograma(self, familiares: list[dict]) -> bytes:
        """Devuelve: PDF del familiograma."""


class FamiliogramaSimulador(FamiliogramaIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def generar_familiograma(self, familiares: list[dict]) -> bytes:
        return b"%PDF-1.4 familiograma de ejemplo"


class FamiliogramaReal(FamiliogramaIntegracion):
    """Cliente del módulo real."""

    def generar_familiograma(self, familiares: list[dict]) -> bytes:
        raise NotImplementedError(_TODO)


def obtener_familiograma() -> FamiliogramaIntegracion:
    if get_settings().integracion_familiograma == "real":
        return FamiliogramaReal()
    return FamiliogramaSimulador()
