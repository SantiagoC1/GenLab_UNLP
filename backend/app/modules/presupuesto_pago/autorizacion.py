"""The administrative user records the answer of the obra social (M4-RF7)."""

from datetime import UTC, datetime

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError
from app.integrations.avisos import AvisosIntegracion
from app.modules.presupuesto_pago.paciente import avisar
from app.modules.presupuesto_pago.repositorio import (
    AUTORIZADO,
    PENDIENTE,
    RECHAZADO,
    EstudioParaPresupuesto,
    RepositorioEstudios,
)
from app.modules.presupuesto_pago.schemas import (
    AutorizacionPendienteSalida,
    AutorizacionRegistradaSalida,
)

NO_ENCONTRADO = "No existe el estudio."


class AutorizacionServicio:
    def __init__(self, repositorio: RepositorioEstudios, avisos: AvisosIntegracion):
        self.repositorio = repositorio
        self.avisos = avisos

    def listar_pendientes(self) -> list[AutorizacionPendienteSalida]:
        return [
            AutorizacionPendienteSalida(
                estudio_id=e.id,
                paciente=e.paciente,
                obra_social=e.cobertura.obra_social,
                porcentaje=e.cobertura.porcentaje,
                importe_usd=e.presupuesto_importe_usd,
                estado_estudio=e.estado,
                motivo_rechazo=e.cobertura.motivo_rechazo,
                con_demanda=e.cobertura.tiene_demanda,
                demanda_nombre=e.cobertura.demanda_nombre,
            )
            for e in self.repositorio.listar_con_cobertura()
            if self.espera_respuesta(e)
        ]

    def registrar_respuesta(
        self, estudio_id: int, resultado: str, motivo: str | None
    ) -> AutorizacionRegistradaSalida:
        estudio = self.repositorio.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError(NO_ENCONTRADO, status_code=404)
        if not self.espera_respuesta(estudio):
            raise BusinessRuleError(
                "El estudio no tiene una autorización de la obra social pendiente.",
                code="sin_autorizacion_pendiente",
            )

        ahora = datetime.now(UTC)
        cobertura = estudio.cobertura
        if resultado == AUTORIZADO:
            # The state model rejects the change if it is not valid, before anything is written.
            self.repositorio.cambiar_estado(estudio.id, EstadoEstudio.AUTORIZADO, ahora)
            cobertura.estado, cobertura.motivo_rechazo = AUTORIZADO, None
            # M4-RF9: Autorizado means authorized and paid. [assumption] P14: the whole budget is
            # recorded, whatever the coverage percentage, until the business defines the rest.
            self.repositorio.registrar_asiento(
                estudio,
                estudio.presupuesto_importe_usd,
                f"obra_social ({cobertura.obra_social})",
                ahora,
            )
            mensaje = (
                f"La obra social {cobertura.obra_social} autorizó su estudio. "
                "Ya puede sacar su turno de extracción."
            )
        else:
            if estudio.estado != EstadoEstudio.RECHAZADO:
                self.repositorio.cambiar_estado(estudio.id, EstadoEstudio.RECHAZADO, ahora)
            cobertura.estado, cobertura.motivo_rechazo = RECHAZADO, motivo.strip()
            mensaje = (
                f"La obra social {cobertura.obra_social} rechazó su estudio. "
                f"Motivo: {cobertura.motivo_rechazo}. Si tiene una decisión judicial favorable, "
                "puede adjuntarla para pedir la reautorización."
            )
        cobertura.resuelta_en = ahora
        # The court decision has been answered: a new one can be attached after a new rejection.
        cobertura.demanda = cobertura.demanda_nombre = cobertura.demanda_en = None
        self.repositorio.guardar_cobertura(estudio.id, cobertura)

        return AutorizacionRegistradaSalida(
            estudio_id=estudio.id,
            estado=estudio.estado,
            resultado=resultado,
            motivo=cobertura.motivo_rechazo,
            paciente_avisado=avisar(self.avisos, estudio.contacto_paciente, mensaje),
        )

    def descargar_demanda(self, estudio_id: int) -> tuple[str, bytes]:
        estudio = self.repositorio.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError(NO_ENCONTRADO, status_code=404)
        cobertura = estudio.cobertura
        if cobertura is None or not cobertura.tiene_demanda:
            raise BusinessRuleError("El estudio no tiene una demanda adjunta.", status_code=404)
        return cobertura.demanda_nombre, cobertura.demanda

    @staticmethod
    def espera_respuesta(estudio: EstudioParaPresupuesto) -> bool:
        """The answer is due for a new coverage, or for a rejected study with a court decision."""
        cobertura = estudio.cobertura
        if cobertura is None:
            return False
        nueva = estudio.estado == EstadoEstudio.CREADO and cobertura.estado == PENDIENTE
        con_demanda = estudio.estado == EstadoEstudio.RECHAZADO and cobertura.tiene_demanda
        return nueva or con_demanda
