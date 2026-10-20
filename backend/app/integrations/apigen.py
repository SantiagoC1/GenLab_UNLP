"""Adaptador del módulo externo MA5."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = (
    "TODO: el contrato real de Apigen todavía no está cerrado (decisión 1 de la especificación)."
)


class ApigenIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        """Devuelve: genes de la patología."""

    @abstractmethod
    def variantes_por_gen(self, gen: str) -> list[dict]:
        """Devuelve: variantes con su clasificación (patogénica, benigna o VUS)."""

    @abstractmethod
    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        """Devuelve: si las variantes confirman el diagnóstico."""


class ApigenSimulador(ApigenIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        return ["GLA"] + (["ACMG-1"] if con_hallazgos_secundarios else [])

    def variantes_por_gen(self, gen: str) -> list[dict]:
        return [{"variante": f"{gen}:c.1A>G", "clasificacion": "VUS"}]

    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        return bool(variantes)


class ApigenReal(ApigenIntegracion):
    """Cliente del módulo real."""

    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        raise NotImplementedError(_TODO)

    def variantes_por_gen(self, gen: str) -> list[dict]:
        raise NotImplementedError(_TODO)

    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        raise NotImplementedError(_TODO)


def obtener_apigen() -> ApigenIntegracion:
    if get_settings().integracion_apigen == "real":
        return ApigenReal()
    return ApigenSimulador()
