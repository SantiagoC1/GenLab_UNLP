"""Storage of the coupons the platform manages (generated, assigned to doctors and patients).

The creation, validity and use of a coupon belong to the external coupons module (MA3); here we
only keep who holds each coupon.

TODO: swap `RepositorioCuponesEnMemoria` for a database-backed implementation (table `coupons`)
without touching the service or the router.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Cupon:
    codigo: str
    descuento: int
    estado: str
    generado_en: datetime
    medico: str | None = None  # contact (e-mail) of the doctor who holds it
    paciente: str | None = None  # contact (e-mail) of the patient it was given to


class RepositorioCupones(ABC):
    @abstractmethod
    def guardar_nuevos(self, cupones: list[Cupon]) -> None: ...

    @abstractmethod
    def listar(self) -> list[Cupon]:
        """Todos los cupones, del más nuevo al más viejo."""

    @abstractmethod
    def obtener(self, codigo: str) -> Cupon | None: ...


class RepositorioCuponesEnMemoria(RepositorioCupones):
    def __init__(self) -> None:
        self.cupones: dict[str, Cupon] = {}

    def guardar_nuevos(self, cupones: list[Cupon]) -> None:
        for cupon in cupones:
            self.cupones[cupon.codigo] = cupon

    def listar(self) -> list[Cupon]:
        return list(reversed(self.cupones.values()))

    def obtener(self, codigo: str) -> Cupon | None:
        return self.cupones.get(codigo)


_repositorio = RepositorioCuponesEnMemoria()


def obtener_repositorio() -> RepositorioCupones:
    return _repositorio
