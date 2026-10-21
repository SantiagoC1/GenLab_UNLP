"""Adaptador del módulo externo MA6."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = "TODO: el contrato real de ObrasSociales todavía no está cerrado (decisión 1 de la especificación)."


class ObrasSocialesIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def listar_obras_sociales(self) -> list[dict]:
        """Devuelve: obras sociales con porcentaje de cobertura."""

    @abstractmethod
    def dar_de_alta_estudio(self, nombre: str, fecha: str) -> str:
        """Devuelve: identificador del estudio ante la obra social."""

    @abstractmethod
    def estado_autorizacion(self, identificador: str) -> str:
        """Devuelve: estado de autorización."""


class ObrasSocialesSimulador(ObrasSocialesIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def listar_obras_sociales(self) -> list[dict]:
        return [{"nombre": "Obra social de ejemplo", "cobertura": 70}]

    def dar_de_alta_estudio(self, nombre: str, fecha: str) -> str:
        return "OS-0001"

    def estado_autorizacion(self, identificador: str) -> str:
        return "Pendiente"


class ObrasSocialesReal(ObrasSocialesIntegracion):
    """Cliente del módulo real."""

    def listar_obras_sociales(self) -> list[dict]:
        raise NotImplementedError(_TODO)

    def dar_de_alta_estudio(self, nombre: str, fecha: str) -> str:
        raise NotImplementedError(_TODO)

    def estado_autorizacion(self, identificador: str) -> str:
        raise NotImplementedError(_TODO)


def obtener_obras_sociales() -> ObrasSocialesIntegracion:
    if get_settings().integracion_obras_sociales == "real":
        return ObrasSocialesReal()
    return ObrasSocialesSimulador()
