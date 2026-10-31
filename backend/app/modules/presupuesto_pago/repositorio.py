"""Access to the studies for the budget, the coverage and the payment.

TODO: the studies table is defined by Integrante A (tasks T1 and 3.4). When it exists, swap
`RepositorioEstudiosEnMemoria` for an implementation backed by the database without touching
the services or the routers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.core.enums import EstadoEstudio
from app.modules.presupuesto_pago.estado import validate_transition

PENDIENTE = "Pendiente"
AUTORIZADO = "Autorizado"
RECHAZADO = "Rechazado"


@dataclass
class Cobertura:
    """Social security coverage of a study (table `authorizations`)."""

    obra_social: str
    porcentaje: int
    estado: str = PENDIENTE
    identificador_externo: str | None = None
    motivo_rechazo: str | None = None
    elegida_en: datetime | None = None
    resuelta_en: datetime | None = None


@dataclass
class AsientoFinanciero:
    """One entry of the financial record: every operation leaves one."""

    id: int
    estudio_id: int
    paciente: str
    importe_usd: int
    metodo: str
    fecha: datetime
    cupon: str | None = None


@dataclass
class CambioEstado:
    desde: EstadoEstudio | None
    hacia: EstadoEstudio
    en: datetime


@dataclass
class EstudioParaPresupuesto:
    id: int
    paciente: str
    contacto_paciente: str
    genes: list[str]
    estado: EstadoEstudio = EstadoEstudio.CREADO
    presupuesto_importe_usd: int | None = None
    presupuesto_emitido_en: datetime | None = None
    cobertura: Cobertura | None = None
    historial: list[CambioEstado] = field(default_factory=list)

    @property
    def tiene_presupuesto(self) -> bool:
        return self.presupuesto_importe_usd is not None


class RepositorioEstudios(ABC):
    @abstractmethod
    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        """Estudios en estado Creado que todavía no tienen presupuesto."""

    @abstractmethod
    def listar_de_paciente(self, contacto: str) -> list[EstudioParaPresupuesto]:
        """Estudios de la cuenta del paciente (identificada por su mail)."""

    @abstractmethod
    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None: ...

    @abstractmethod
    def guardar_presupuesto(
        self, estudio_id: int, importe_usd: int, emitido_en: datetime
    ) -> EstudioParaPresupuesto:
        """Publica el presupuesto del estudio."""

    @abstractmethod
    def guardar_cobertura(self, estudio_id: int, cobertura: Cobertura) -> EstudioParaPresupuesto:
        """Guarda la cobertura por obra social del estudio."""

    @abstractmethod
    def cambiar_estado(
        self, estudio_id: int, nuevo: EstadoEstudio, en: datetime
    ) -> EstudioParaPresupuesto:
        """Cambia el estado si la transición es válida y la deja en el historial."""

    @abstractmethod
    def registrar_asiento(
        self,
        estudio: EstudioParaPresupuesto,
        importe_usd: int,
        metodo: str,
        fecha: datetime,
        cupon: str | None = None,
    ) -> AsientoFinanciero:
        """Asienta una operación en el registro financiero."""

    @abstractmethod
    def listar_asientos(self) -> list[AsientoFinanciero]:
        """El registro financiero, del más reciente al más antiguo."""


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
        self.asientos: list[AsientoFinanciero] = []

    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if not e.tiene_presupuesto]

    def listar_de_paciente(self, contacto: str) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if e.contacto_paciente == contacto]

    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None:
        return self.estudios.get(estudio_id)

    def guardar_presupuesto(
        self, estudio_id: int, importe_usd: int, emitido_en: datetime
    ) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.presupuesto_importe_usd = importe_usd
        estudio.presupuesto_emitido_en = emitido_en
        return estudio

    def guardar_cobertura(self, estudio_id: int, cobertura: Cobertura) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.cobertura = cobertura
        return estudio

    def cambiar_estado(
        self, estudio_id: int, nuevo: EstadoEstudio, en: datetime
    ) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        validate_transition(estudio.estado, nuevo)
        estudio.historial.append(CambioEstado(estudio.estado, nuevo, en))
        estudio.estado = nuevo
        return estudio

    def registrar_asiento(
        self,
        estudio: EstudioParaPresupuesto,
        importe_usd: int,
        metodo: str,
        fecha: datetime,
        cupon: str | None = None,
    ) -> AsientoFinanciero:
        asiento = AsientoFinanciero(
            len(self.asientos) + 1, estudio.id, estudio.paciente, importe_usd, metodo, fecha, cupon
        )
        self.asientos.append(asiento)
        return asiento

    def listar_asientos(self) -> list[AsientoFinanciero]:
        return list(reversed(self.asientos))


_repositorio = RepositorioEstudiosEnMemoria()


def obtener_repositorio() -> RepositorioEstudios:
    return _repositorio
