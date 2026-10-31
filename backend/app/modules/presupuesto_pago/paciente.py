"""What the patient can do with their own studies: coverage, payment and reauthorization."""

from datetime import UTC, datetime

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.integrations.obras_sociales import ObrasSocialesIntegracion
from app.modules.presupuesto_pago.repositorio import (
    PENDIENTE,
    Cobertura,
    EstudioParaPresupuesto,
    RepositorioEstudios,
)
from app.modules.presupuesto_pago.schemas import (
    CoberturaSalida,
    EstudioDelPacienteSalida,
    ObraSocialSalida,
)

INTEGRACION_OBRAS_SOCIALES = "obras_sociales"


class PacienteServicio:
    def __init__(
        self,
        repositorio: RepositorioEstudios,
        obras_sociales: ObrasSocialesIntegracion,
    ):
        self.repositorio = repositorio
        self.obras_sociales = obras_sociales

    # --- reading --------------------------------------------------------------------------

    def listar_estudios(self, contacto: str) -> list[EstudioDelPacienteSalida]:
        return [self._salida(e) for e in self.repositorio.listar_de_paciente(contacto)]

    def listar_obras_sociales(self) -> list[ObraSocialSalida]:
        try:
            items = self.obras_sociales.listar_obras_sociales()
        except Exception:
            raise InvalidIntegration(INTEGRACION_OBRAS_SOCIALES) from None
        return [ObraSocialSalida(nombre=i["nombre"], cobertura=i["cobertura"]) for i in items]

    # --- M4-RF3 and M4-RF4: choose the social security coverage -----------------------------

    def elegir_cobertura(
        self, contacto: str, estudio_id: int, obra_social: str
    ) -> EstudioDelPacienteSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        self._exigir_presupuesto_sin_resolver(estudio)
        if estudio.cobertura is not None:
            raise BusinessRuleError(
                "El estudio ya está a la espera de la autorización de la obra social."
                if estudio.cobertura.estado == PENDIENTE
                else "Ya elegiste una cobertura para este estudio.",
                code="cobertura_ya_elegida",
            )

        elegida = next((o for o in self.listar_obras_sociales() if o.nombre == obra_social), None)
        if elegida is None:
            raise BusinessRuleError(
                "Tu obra social no figura en la lista: solo podés pagar de forma particular.",
                code="obra_social_no_listada",
            )

        ahora = datetime.now(UTC)
        try:
            identificador = self.obras_sociales.dar_de_alta_estudio(
                f"Estudio {estudio.id} - {estudio.paciente}", ahora.date().isoformat()
            )
        except Exception:
            raise InvalidIntegration(INTEGRACION_OBRAS_SOCIALES) from None

        cobertura = Cobertura(
            obra_social=elegida.nombre,
            porcentaje=elegida.cobertura,
            identificador_externo=identificador,
            elegida_en=ahora,
        )
        # The study stays in Creado until the administrative user records the answer.
        return self._salida(self.repositorio.guardar_cobertura(estudio.id, cobertura))

    # --- helpers --------------------------------------------------------------------------

    def estudio_del_paciente(self, contacto: str, estudio_id: int) -> EstudioParaPresupuesto:
        estudio = self.repositorio.obtener(estudio_id)
        # Someone else's study looks the same as a missing one.
        if estudio is None or estudio.contacto_paciente != contacto:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        return estudio

    @staticmethod
    def _exigir_presupuesto_sin_resolver(estudio: EstudioParaPresupuesto) -> None:
        if not estudio.tiene_presupuesto:
            raise BusinessRuleError("El estudio todavía no tiene el presupuesto emitido.")
        if estudio.estado != EstadoEstudio.CREADO:
            raise BusinessRuleError(
                f"El estudio ya está {estudio.estado.value}: no admite elegir la cobertura."
            )

    @staticmethod
    def _salida(estudio: EstudioParaPresupuesto) -> EstudioDelPacienteSalida:
        cobertura = estudio.cobertura
        return EstudioDelPacienteSalida(
            id=estudio.id,
            estado=estudio.estado,
            cantidad_genes=len(estudio.genes),
            importe_usd=estudio.presupuesto_importe_usd,
            cobertura=None
            if cobertura is None
            else CoberturaSalida(
                obra_social=cobertura.obra_social,
                porcentaje=cobertura.porcentaje,
                estado=cobertura.estado,
                motivo_rechazo=cobertura.motivo_rechazo,
            ),
        )
