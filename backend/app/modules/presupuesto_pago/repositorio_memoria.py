"""Studies kept in memory, with example data.

Only for `DEV_AUTH=true` (nothing is written to the database) and as the test double of the
`RepositorioEstudios` interface. The real implementation is in repositorio_supabase.py.
"""

from datetime import datetime

from app.core.enums import EstadoEstudio
from app.modules.presupuesto_pago.estado import validate_transition
from app.modules.presupuesto_pago.repositorio import (
    AsientoFinanciero,
    CambioEstado,
    Cobertura,
    CuponAplicado,
    EstudioParaPresupuesto,
    RepositorioEstudios,
)


def _estudios_de_ejemplo() -> list[EstudioParaPresupuesto]:
    return [
        EstudioParaPresupuesto(
            1,
            "Lucía Fernández",
            "lucia.fernandez@example.com",
            ["GBA", "GLA", "IDUA"],
            contacto_medico="ana.perez@example.com",
        ),
        EstudioParaPresupuesto(
            2,
            "Martín Gómez",
            "martin.gomez@example.com",
            ["GBA", "GLA", "IDUA", "IDS", "NPC1", "NPC2", "GAA", "ARSA"],
            contacto_medico="ana.perez@example.com",
        ),
        EstudioParaPresupuesto(
            3,
            "Sofía Ramírez",
            "sofia.ramirez@example.com",
            ["GBA", "GLA", "IDUA", "IDS", "NPC1"],
            contacto_medico="carlos.rivas@example.com",
        ),
    ]


class RepositorioEstudiosEnMemoria(RepositorioEstudios):
    """Example data to develop and demo without the database."""

    def __init__(self) -> None:
        self.estudios = {e.id: e for e in _estudios_de_ejemplo()}
        self.asientos: list[AsientoFinanciero] = []

    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if not e.tiene_presupuesto]

    def listar_con_cobertura(self) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if e.cobertura is not None]

    def listar_de_paciente(self, contacto: str) -> list[EstudioParaPresupuesto]:
        return [e for e in self.estudios.values() if e.contacto_paciente == contacto]

    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None:
        return self.estudios.get(estudio_id)

    def guardar_presupuesto(
        self,
        estudio_id: int,
        importe_usd: int,
        emitido_en: datetime,
        emitido_por: str | None = None,
    ) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.presupuesto_importe_usd = importe_usd
        estudio.presupuesto_emitido_en = emitido_en
        return estudio

    def guardar_cobertura(self, estudio_id: int, cobertura: Cobertura) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.cobertura = cobertura
        return estudio

    def guardar_cupon_aplicado(
        self, estudio_id: int, cupon: CuponAplicado | None
    ) -> EstudioParaPresupuesto:
        estudio = self.estudios[estudio_id]
        estudio.cupon_aplicado = cupon
        return estudio

    def cambiar_estado(
        self,
        estudio_id: int,
        nuevo: EstadoEstudio,
        en: datetime,
        cambiado_por: str | None = None,
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
        cuotas: int | None = None,
        valor_cuota: float | None = None,
        mp_payment_id: str | None = None,
    ) -> AsientoFinanciero:
        asiento = AsientoFinanciero(
            len(self.asientos) + 1,
            estudio.id,
            estudio.paciente,
            importe_usd,
            metodo,
            fecha,
            cupon,
            cuotas,
            valor_cuota,
            mp_payment_id,
        )
        self.asientos.append(asiento)
        return asiento

    def buscar_asiento_por_pago_mp(self, mp_payment_id: str) -> AsientoFinanciero | None:
        return next((a for a in self.asientos if a.mp_payment_id == mp_payment_id), None)

    def listar_asientos(self) -> list[AsientoFinanciero]:
        return list(reversed(self.asientos))

    def obtener_demanda(self, estudio_id: int) -> bytes | None:
        estudio = self.estudios.get(estudio_id)
        return None if estudio is None or estudio.cobertura is None else estudio.cobertura.demanda


_repositorio = RepositorioEstudiosEnMemoria()


def repositorio_en_memoria() -> RepositorioEstudiosEnMemoria:
    return _repositorio
