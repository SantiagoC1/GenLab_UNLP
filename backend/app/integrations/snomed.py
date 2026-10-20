"""Adaptador del módulo externo MA2."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = (
    "TODO: el contrato real de Snomed todavía no está cerrado (decisión 1 de la especificación)."
)


class SnomedIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def buscar_terminos(self, texto: str, pagina: int = 1) -> list[dict]:
        """Devuelve: términos que coinciden (3 letras o más, con paginación)."""


class SnomedSimulador(SnomedIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def buscar_terminos(self, texto: str, pagina: int = 1) -> list[dict]:
        return [{"codigo": "1", "termino": f"{texto} (ejemplo)"}]


class SnomedReal(SnomedIntegracion):
    """Cliente del módulo real."""

    def buscar_terminos(self, texto: str, pagina: int = 1) -> list[dict]:
        raise NotImplementedError(_TODO)


def obtener_snomed() -> SnomedIntegracion:
    if get_settings().integracion_snomed == "real":
        return SnomedReal()
    return SnomedSimulador()
