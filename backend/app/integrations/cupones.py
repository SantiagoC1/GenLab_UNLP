"""Adaptador del módulo externo MA3."""

from abc import ABC, abstractmethod

from app.core.config import get_settings


class CuponesError(Exception):
    """El módulo de cupones rechazó la solicitud (por ejemplo, un descuento inválido)."""


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

    def recordar_cupones(self, cupones: list[dict]) -> None:
        """Le cuenta al módulo qué cupones guarda la plataforma (código, descuento y estado).

        El módulo real los conoce por su cuenta, así que no hace nada. Solo lo usa el simulador.
        """
        return None


# Cupones que emitió el simulador (el módulo real los guarda por su cuenta).
_EMITIDOS: dict[str, dict] = {}


def reiniciar_simulador() -> None:
    """Borra los cupones emitidos por el simulador. Lo usan los tests."""
    _EMITIDOS.clear()


def _numero(codigo: str) -> int:
    """El número de un código CUP-0007, o 0 si el código no tiene esa forma."""
    prefijo, _, numero = codigo.partition("-")
    return int(numero) if prefijo == "CUP" and numero.isdigit() else 0


class CuponesSimulador(CuponesIntegracion):
    """Emite, valida y marca cupones en memoria, para demostrar sin depender de otro grupo.

    Al reiniciar el backend olvida lo que emitió, pero la plataforma conserva los cupones en su
    base: por eso la plataforma se los recuerda con `recordar_cupones` antes de preguntarle.
    """

    def recordar_cupones(self, cupones: list[dict]) -> None:
        for cupon in cupones:
            _EMITIDOS.setdefault(
                cupon["codigo"],
                {
                    "codigo": cupon["codigo"],
                    "descuento": cupon["descuento"],
                    "estado": cupon["estado"],
                },
            )

    def obtener_cupones(self, descuento: int, cantidad: int) -> list[dict]:
        if not 1 <= descuento <= 100:
            raise CuponesError("El descuento tiene que estar entre 1 y 100.")
        if not 1 <= cantidad <= 100:
            raise CuponesError("La cantidad tiene que estar entre 1 y 100.")
        nuevos = []
        for _ in range(cantidad):
            codigo = f"CUP-{max(map(_numero, _EMITIDOS), default=0) + 1:04d}"
            cupon = {"codigo": codigo, "descuento": descuento, "estado": "Vigente"}
            _EMITIDOS[codigo] = cupon
            nuevos.append(dict(cupon))
        return nuevos

    def validar_cupon(self, codigo: str) -> dict:
        cupon = _EMITIDOS.get(codigo)
        if cupon is None:
            return {"codigo": codigo, "descuento": 0, "estado": "Inexistente"}
        return dict(cupon)

    def marcar_cupon_usado(self, codigo: str) -> dict:
        cupon = _EMITIDOS.get(codigo)
        if cupon is None:
            raise CuponesError("El cupón no existe.")
        cupon["estado"] = "Usado"
        return dict(cupon)


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
