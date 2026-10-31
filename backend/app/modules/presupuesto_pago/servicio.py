from datetime import UTC, datetime

from app.core.errors import BusinessRuleError
from app.integrations.avisos import AvisosIntegracion
from app.modules.presupuesto_pago.repositorio import EstudioParaPresupuesto, RepositorioEstudios
from app.modules.presupuesto_pago.schemas import (
    DetalleEstudioSalida,
    EstudioPendienteSalida,
    PresupuestoEmitidoSalida,
)
from app.modules.presupuesto_pago.tarifa import calcular_importe

CANAL_AVISO = "email"


class PresupuestoServicio:
    def __init__(self, repositorio: RepositorioEstudios, avisos: AvisosIntegracion):
        self.repositorio = repositorio
        self.avisos = avisos

    def listar_pendientes(self) -> list[EstudioPendienteSalida]:
        return [
            EstudioPendienteSalida(id=e.id, paciente=e.paciente, cantidad_genes=len(e.genes))
            for e in self.repositorio.listar_creados_sin_presupuesto()
        ]

    def detalle(self, estudio_id: int) -> DetalleEstudioSalida:
        estudio = self._estudio(estudio_id)
        return DetalleEstudioSalida(
            id=estudio.id,
            paciente=estudio.paciente,
            genes=estudio.genes,
            cantidad_genes=len(estudio.genes),
            importe_usd=calcular_importe(len(estudio.genes)),
            presupuesto_emitido=estudio.tiene_presupuesto,
        )

    def emitir(self, estudio_id: int) -> PresupuestoEmitidoSalida:
        estudio = self._estudio(estudio_id)
        if estudio.tiene_presupuesto:
            raise BusinessRuleError("El estudio ya tiene el presupuesto emitido.")
        importe = calcular_importe(len(estudio.genes))
        emitido_en = datetime.now(UTC)
        self.repositorio.guardar_presupuesto(estudio.id, importe, emitido_en)
        # [supuesto] M4-RF2: el paciente recibe un aviso al publicarse el presupuesto.
        avisado = self.avisos.enviar_aviso(
            estudio.contacto_paciente,
            CANAL_AVISO,
            f"Ya está disponible el presupuesto de su estudio: USD {importe}, "
            "con la extracción y el turno incluidos.",
        )
        return PresupuestoEmitidoSalida(
            estudio_id=estudio.id,
            importe_usd=importe,
            emitido_en=emitido_en,
            paciente_avisado=avisado,
        )

    def _estudio(self, estudio_id: int) -> EstudioParaPresupuesto:
        estudio = self.repositorio.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        return estudio
