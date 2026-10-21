"""Adaptador del módulo externo MA7."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = (
    "TODO: el contrato real de Avisos todavía no está cerrado (decisión 1 de la especificación)."
)


class AvisosIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        """Devuelve: confirmación de envío."""


class AvisosSimulador(AvisosIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        return True


class AvisosReal(AvisosIntegracion):
    """Cliente del módulo real."""

    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        raise NotImplementedError(_TODO)


def obtener_avisos() -> AvisosIntegracion:
    if get_settings().integracion_avisos == "real":
        return AvisosReal()
    return AvisosSimulador()
