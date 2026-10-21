"""Acceso a los estudios para el presupuesto.

TODO: la tabla de estudios la define el Integrante A (tareas T1 y 3.4). Cuando exista, se
reemplaza `RepositorioEstudiosEnMemoria` por una implementación con SQLAlchemy sin tocar el
servicio ni el router.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EstudioParaPresupuesto:
    id: int
    paciente: str
    contacto_paciente: str
    genes: list[str]
    presupuesto_importe_usd: int | None = None
    presupuesto_emitido_en: datetime | None = None

    @property
    def tiene_presupuesto(self) -> bool:
        return self.presupuesto_importe_usd is not None


class RepositorioEstudios(ABC):
    @abstractmethod
    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        """Estudios en estado Creado que todavía no tienen presupuesto."""

    @abstractmethod
    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None: ...

    @abstractmethod
    def guardar_presupuesto(
        self, estudio_id: int, importe_usd: int, emitido_en: datetime
    ) -> EstudioParaPresupuesto:
        """Publica el presupuesto del estudio."""


def _estudios_de_ejemplo() -> list[EstudioParaPresupuesto]:
    return [
        EstudioParaPresupuesto(
            1, "Lucía Fernández", "lucia.fernandez@example.com", ["GBA", "GLA", "IDUA"]
        ),
        EstudioParaPresupuesto(
            2,
            "Martín Gómez",
            "martin.gomez@example.com",
            ["GBA", "GLA", "IDUA", "IDS", "NPC1", "NPC2", "GAA", "ARSA"],
        ),
        EstudioParaPresupuesto(
            3,
            "Sofía Ramírez",
            "sofia.ramirez@example.com",
            ["GBA", "GLA", "IDUA", "IDS", "NPC1"],
        ),
    ]


class RepositorioEstudiosEnMemoria(RepositorioEstudios):
    """Datos de ejemplo para desarrollar y demostrar sin la tabla de estudios."""

    def __init__(self) -> None:
        self.estudios = {e.id: e for e in _estudios_de_ejemplo()}

    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if not e.tiene_presupuesto]

    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None:
        return self.estudios.get(estudio_id)

    def guardar_presupuesto(
        self, estudio_id: int, importe_usd: int, emitido_en: datetime
    ) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.presupuesto_importe_usd = importe_usd
        estudio.presupuesto_emitido_en = emitido_en
        return estudio


_repositorio = RepositorioEstudiosEnMemoria()


def obtener_repositorio() -> RepositorioEstudios:
    return _repositorio
