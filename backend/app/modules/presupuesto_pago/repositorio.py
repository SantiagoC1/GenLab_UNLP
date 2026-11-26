"""Access to the studies for the budget, the coverage and the payment.

`RepositorioEstudiosSupabase` (repositorio_supabase.py) is the real implementation. The one in
memory (repositorio_memoria.py) only serves `DEV_AUTH=true` and the tests.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.core import dev_auth
from app.core.enums import EstadoEstudio

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
    registrada_por: str | None = None  # id of the user who recorded the answer
    # Court decision attached by the patient to ask for the reauthorization (M4-RF8).
    demanda_nombre: str | None = None
    demanda: bytes | None = None
    demanda_en: datetime | None = None

    @property
    def tiene_demanda(self) -> bool:
        # The listings do not load the PDF itself: the name tells whether there is one.
        return self.demanda_nombre is not None


@dataclass(frozen=True)
class CuponAplicado:
    codigo: str
    descuento: int  # percentage


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
    contacto_medico: str = ""  # who requested the study: notified about a resampling
    cobertura: Cobertura | None = None
    cupon_aplicado: CuponAplicado | None = None
    historial: list[CambioEstado] = field(default_factory=list)

    @property
    def tiene_presupuesto(self) -> bool:
        return self.presupuesto_importe_usd is not None


class RepositorioEstudios(ABC):
    @abstractmethod
    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        """Estudios en estado Creado que todavía no tienen presupuesto."""

    @abstractmethod
    def listar_con_cobertura(self) -> list[EstudioParaPresupuesto]:
        """Estudios en los que el paciente eligió la cobertura por obra social."""

    @abstractmethod
    def listar_de_paciente(self, contacto: str) -> list[EstudioParaPresupuesto]:
        """Estudios de la cuenta del paciente (identificada por su mail)."""

    @abstractmethod
    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None: ...

    @abstractmethod
    def guardar_presupuesto(
        self,
        estudio_id: int,
        importe_usd: int,
        emitido_en: datetime,
        emitido_por: str | None = None,
    ) -> EstudioParaPresupuesto:
        """Publica el presupuesto del estudio. `emitido_por` es el id del usuario que lo emite."""

    @abstractmethod
    def guardar_cobertura(self, estudio_id: int, cobertura: Cobertura) -> EstudioParaPresupuesto:
        """Guarda la cobertura por obra social del estudio."""

    @abstractmethod
    def guardar_cupon_aplicado(
        self, estudio_id: int, cupon: CuponAplicado | None
    ) -> EstudioParaPresupuesto:
        """Guarda (o quita) el cupón que el paciente aplicó antes de pagar."""

    @abstractmethod
    def cambiar_estado(
        self,
        estudio_id: int,
        nuevo: EstadoEstudio,
        en: datetime,
        cambiado_por: str | None = None,
    ) -> EstudioParaPresupuesto:
        """Cambia el estado si la transición es válida y la deja en el historial.

        Devuelve el estudio ya actualizado: quien llama debe leer el estado de ese resultado.
        """

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

    @abstractmethod
    def obtener_demanda(self, estudio_id: int) -> bytes | None:
        """El PDF de la demanda adjunta (los listados no lo traen)."""


def obtener_repositorio() -> RepositorioEstudios:
    if dev_auth.is_enabled():
        from app.modules.presupuesto_pago.repositorio_memoria import repositorio_en_memoria

        return repositorio_en_memoria()
    from app.modules.presupuesto_pago.repositorio_supabase import RepositorioEstudiosSupabase

    return RepositorioEstudiosSupabase()
