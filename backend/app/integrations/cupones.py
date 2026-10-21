"""Adaptador del módulo externo MA3."""

from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = (
    "TODO: el contrato real de Cupones todavía no está cerrado (decisión 1 de la especificación)."
)


class CuponesIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        """Devuelve: cupones nuevos con su estado."""

    @abstractmethod
    def validar_cupon(self, codigo: str) -> dict:
        """Devuelve: cupón con estado (fecha y no uso)."""

    @abstractmethod
    def marcar_cupon_usado(self, codigo: str) -> dict:
        """Devuelve: cupón marcado como usado."""


class CuponesSimulador(CuponesIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        return [
            {"codigo": f"CUP-{i:04d}", "descuento": descuento, "estado": "Vigente"}
            for i in range(cantidad)
        ]

    def validar_cupon(self, codigo: str) -> dict:
        return {"codigo": codigo, "descuento": 10, "estado": "Vigente"}

    def marcar_cupon_usado(self, codigo: str) -> dict:
        return {"codigo": codigo, "estado": "Usado"}


class CuponesReal(CuponesIntegracion):
    """Cliente del módulo real."""

    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        raise NotImplementedError(_TODO)

    def validar_cupon(self, codigo: str) -> dict:
        raise NotImplementedError(_TODO)

    def marcar_cupon_usado(self, codigo: str) -> dict:
        raise NotImplementedError(_TODO)


def obtener_cupones() -> CuponesIntegracion:
    if get_settings().integracion_cupones == "real":
        return CuponesReal()
    return CuponesSimulador()
