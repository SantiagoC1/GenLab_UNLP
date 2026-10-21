"""Adaptador del módulo externo MA9."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de OptimizacionRecorrido todavía no está cerrado (decisión 1 de la especificación)."


class OptimizacionRecorridoIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def ordenar_recorrido(self, direcciones: list[str]) -> list[str]:
        """Devuelve: direcciones en el orden del recorrido."""


class OptimizacionRecorridoSimulador(OptimizacionRecorridoIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def ordenar_recorrido(self, direcciones: list[str]) -> list[str]:
        return list(direcciones)


class OptimizacionRecorridoReal(OptimizacionRecorridoIntegracion):
    """Cliente del módulo real."""

    def ordenar_recorrido(self, direcciones: list[str]) -> list[str]:
        raise NotImplementedError(_TODO)


def obtener_optimizacion_recorrido() -> OptimizacionRecorridoIntegracion:
    if get_settings().integracion_optimizacion_recorrido == "real":
        return OptimizacionRecorridoReal()
    return OptimizacionRecorridoSimulador()
