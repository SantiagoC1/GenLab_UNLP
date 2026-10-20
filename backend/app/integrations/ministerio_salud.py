"""Adaptador del módulo externo API del Ministerio de Salud (a cargo del grupo)."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de MinisterioSalud todavía no está cerrado (decisión 1 de la especificación)."


class MinisterioSaludIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def solicitar_permiso(self, csv_pacientes: bytes) -> bytes:
        """Devuelve: permiso en PDF."""


class MinisterioSaludSimulador(MinisterioSaludIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def solicitar_permiso(self, csv_pacientes: bytes) -> bytes:
        return b"%PDF-1.4 permiso de ejemplo"


class MinisterioSaludReal(MinisterioSaludIntegracion):
    """Cliente del módulo real."""

    def solicitar_permiso(self, csv_pacientes: bytes) -> bytes:
        raise NotImplementedError(_TODO)


def obtener_ministerio_salud() -> MinisterioSaludIntegracion:
    if get_settings().integracion_ministerio_salud == "real":
        return MinisterioSaludReal()
    return MinisterioSaludSimulador()
