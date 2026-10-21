"""Adaptador del módulo externo MA10."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de Fedex todavía no está cerrado (decisión 1 de la especificación)."


class FedexIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def programar_retiro(self, dia: str, hora: str, lugar: str) -> str:
        """Devuelve: URL de consulta de estado."""

    @abstractmethod
    def consultar_estado(self, url: str) -> str:
        """Devuelve: estado del envío."""


class FedexSimulador(FedexIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def programar_retiro(self, dia: str, hora: str, lugar: str) -> str:
        return "https://fedex.example/estado/ejemplo"

    def consultar_estado(self, url: str) -> str:
        return "Programado"


class FedexReal(FedexIntegracion):
    """Cliente del módulo real."""

    def programar_retiro(self, dia: str, hora: str, lugar: str) -> str:
        raise NotImplementedError(_TODO)

    def consultar_estado(self, url: str) -> str:
        raise NotImplementedError(_TODO)


def obtener_fedex() -> FedexIntegracion:
    if get_settings().integracion_fedex == "real":
        return FedexReal()
    return FedexSimulador()
