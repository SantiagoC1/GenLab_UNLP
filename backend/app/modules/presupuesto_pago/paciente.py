"""What the patient can do with their own studies: coverage, payment and reauthorization."""

import re
from datetime import UTC, datetime
from urllib.parse import unquote

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.documentos.pdf import MAX_UPLOAD_BYTES, is_pdf
from app.integrations.avisos import AvisosIntegracion
from app.integrations.cupones import CuponesIntegracion
from app.integrations.obras_sociales import ObrasSocialesIntegracion
from app.modules.cupones.repositorio import RepositorioCupones
from app.modules.presupuesto_pago.repositorio import (
    PENDIENTE,
    Cobertura,
    CuponAplicado,
    EstudioParaPresupuesto,
    RepositorioEstudios,
)
from app.modules.presupuesto_pago.schemas import (
    CoberturaSalida,
    CuponAplicadoSalida,
    DemandaEnviadaSalida,
    EstudioDelPacienteSalida,
    ObraSocialSalida,
    PagoSalida,
)

INTEGRACION_OBRAS_SOCIALES = "obras_sociales"
INTEGRACION_CUPONES = "cupones"
VIGENTE = "Vigente"
# Who receives the notice when a court decision arrives. [assumption] A role label: resolving it
# to real addresses belongs to the notices module (M9).
DESTINO_ADMINISTRATIVO = "administrativo_laboratorio"
# The coupon PDFs the platform issues print the code after the label "Código:".
CODIGO_EN_EL_PDF = re.compile(rb"C.digo:\s*([A-Za-z0-9_-]{3,64})")


def importe_con_descuento(importe_usd: int, descuento: int) -> int:
    """Applies the percentage and rounds to whole dollars (half up)."""
    return (importe_usd * (100 - descuento) + 50) // 100


CANAL_AVISO = "email"
METODO_PAGO_SIMULADO = "simulado"


def avisar(avisos: AvisosIntegracion, destinatario: str, mensaje: str) -> bool:
    """A failing notice never undoes the operation that triggered it."""
    try:
        return avisos.enviar_aviso(destinatario, CANAL_AVISO, mensaje)
    except Exception:
        return False


class PacienteServicio:
    def __init__(
        self,
        repositorio: RepositorioEstudios,
        obras_sociales: ObrasSocialesIntegracion,
        avisos: AvisosIntegracion,
        cupones: CuponesIntegracion,
        repositorio_cupones: RepositorioCupones,
    ):
        self.repositorio = repositorio
        self.obras_sociales = obras_sociales
        self.avisos = avisos
        self.cupones = cupones
        self.repositorio_cupones = repositorio_cupones

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

    # --- M4-RF5 and M4-RF9: private payment, simulated --------------------------------------

    def pagar(self, contacto: str, estudio_id: int, metodo: str) -> PagoSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        self._exigir_pago_posible(estudio)

        original = estudio.presupuesto_importe_usd
        importe = original
        codigo = None
        if estudio.cupon_aplicado is not None:
            # The coupon may have been used or expired since it was applied: ask again.
            cupon = self._validar_cupon(estudio.cupon_aplicado.codigo)
            if cupon["estado"] != VIGENTE:
                self.repositorio.guardar_cupon_aplicado(estudio.id, None)
                raise BusinessRuleError(
                    f"El cupón {cupon['codigo']} ya no está Vigente ({cupon['estado']}): "
                    "se mantiene el importe original.",
                    code="cupon_no_vigente",
                )
            codigo = cupon["codigo"]
            importe = importe_con_descuento(original, cupon["descuento"])

        informado = False
        if codigo is not None:
            # M4-RF6: the use is reported to the coupons module. Nothing is recorded if it fails.
            try:
                self.cupones.marcar_cupon_usado(codigo)
            except Exception:
                raise InvalidIntegration(INTEGRACION_CUPONES) from None
            self.repositorio_cupones.marcar_usado(codigo)
            informado = True

        ahora = datetime.now(UTC)
        # Nothing is recorded before this point, so leaving without paying changes nothing.
        self.repositorio.cambiar_estado(estudio.id, EstadoEstudio.PAGADO, ahora)
        asiento = self.repositorio.registrar_asiento(estudio, importe, metodo, ahora, codigo)
        avisado = avisar(
            self.avisos,
            estudio.contacto_paciente,
            f"Recibimos el pago de su estudio (USD {importe}). Ya puede sacar su turno de extracción.",
        )
        return PagoSalida(
            estudio_id=estudio.id,
            estado=estudio.estado,
            importe_original_usd=original,
            importe_usd=asiento.importe_usd,
            cupon=codigo,
            cupon_informado=informado,
            metodo=asiento.metodo,
            pagado_en=asiento.fecha,
            paciente_avisado=avisado,
        )

    # --- M4-RF6: apply a discount coupon ------------------------------------------------------

    def aplicar_cupon(self, contacto: str, estudio_id: int, codigo: str) -> CuponAplicadoSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        self._exigir_pago_posible(estudio)
        codigo = codigo.strip()

        conocido = self.repositorio_cupones.obtener(codigo)
        # A coupon the platform handed out can only be used by the patient who received it.
        if conocido is not None and conocido.paciente != contacto:
            raise BusinessRuleError(
                "Ese cupón no está asignado a tu cuenta.", code="cupon_de_otro_paciente"
            )

        cupon = self._validar_cupon(codigo)
        if cupon["estado"] != VIGENTE:
            # The reason is shown and the original amount is kept.
            raise BusinessRuleError(
                f"El cupón {codigo} no se puede aplicar: su estado es {cupon['estado']}.",
                code="cupon_no_vigente",
            )
        aplicado = CuponAplicado(cupon["codigo"], cupon["descuento"])
        self.repositorio.guardar_cupon_aplicado(estudio.id, aplicado)
        return self._cupon_salida(estudio, aplicado)

    def aplicar_cupon_con_pdf(
        self, contacto: str, estudio_id: int, contenido: bytes
    ) -> CuponAplicadoSalida:
        self.exigir_pdf(contenido)
        encontrado = CODIGO_EN_EL_PDF.search(contenido)
        if encontrado is None:
            raise BusinessRuleError(
                "No se encontró el código del cupón en el PDF. Probá ingresando el código.",
                status_code=422,
                code="cupon_sin_codigo",
            )
        return self.aplicar_cupon(contacto, estudio_id, encontrado.group(1).decode())

    @staticmethod
    def exigir_pdf(contenido: bytes) -> None:
        """Only real PDFs are accepted, whatever the name or the declared type says."""
        if not contenido:
            raise BusinessRuleError("El archivo está vacío.", status_code=422)
        if len(contenido) > MAX_UPLOAD_BYTES:
            raise BusinessRuleError("El archivo pesa más de 5 MB.", status_code=413)
        if not is_pdf(contenido):
            raise BusinessRuleError(
                "El archivo no es un PDF.", status_code=422, code="archivo_no_pdf"
            )

    # --- M4-RF8: request the reauthorization with a court decision ---------------------------

    def enviar_demanda(
        self, contacto: str, estudio_id: int, contenido: bytes, nombre: str | None
    ) -> DemandaEnviadaSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        cobertura = estudio.cobertura
        if estudio.estado != EstadoEstudio.RECHAZADO or cobertura is None:
            raise BusinessRuleError(
                "Solo se puede pedir la reautorización de un estudio Rechazado.",
                code="estudio_no_rechazado",
            )
        if cobertura.tiene_demanda:
            raise BusinessRuleError(
                "Ya enviaste la demanda: el laboratorio está revisando la reautorización.",
                code="demanda_ya_enviada",
            )
        self.exigir_pdf(contenido)

        cobertura.demanda = contenido
        cobertura.demanda_nombre = (unquote(nombre or "").strip() or "demanda.pdf")[:120]
        cobertura.demanda_en = datetime.now(UTC)
        self.repositorio.guardar_cobertura(estudio.id, cobertura)
        # [assumption] scenario 19: the administrative user is notified.
        avisado = avisar(
            self.avisos,
            DESTINO_ADMINISTRATIVO,
            f"{estudio.paciente} adjuntó una demanda para pedir la reautorización del "
            f"estudio {estudio.id} ({cobertura.obra_social}).",
        )
        return DemandaEnviadaSalida(
            estudio_id=estudio.id,
            estado=estudio.estado,
            demanda_nombre=cobertura.demanda_nombre,
            administrativo_avisado=avisado,
        )

    def quitar_cupon(self, contacto: str, estudio_id: int) -> EstudioDelPacienteSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        return self._salida(self.repositorio.guardar_cupon_aplicado(estudio.id, None))

    def _validar_cupon(self, codigo: str) -> dict:
        try:
            return self.cupones.validar_cupon(codigo)
        except Exception:
            raise InvalidIntegration(INTEGRACION_CUPONES) from None

    @staticmethod
    def _cupon_salida(estudio: EstudioParaPresupuesto, cupon: CuponAplicado) -> CuponAplicadoSalida:
        return CuponAplicadoSalida(
            codigo=cupon.codigo,
            descuento=cupon.descuento,
            importe_original_usd=estudio.presupuesto_importe_usd,
            importe_con_descuento_usd=importe_con_descuento(
                estudio.presupuesto_importe_usd, cupon.descuento
            ),
        )

    @staticmethod
    def _exigir_pago_posible(estudio: EstudioParaPresupuesto) -> None:
        if not estudio.tiene_presupuesto:
            raise BusinessRuleError("El estudio todavía no tiene el presupuesto emitido.")
        if estudio.estado in (EstadoEstudio.PAGADO, EstadoEstudio.AUTORIZADO):
            # M4-RF9: an Autorizado study is authorized and paid.
            raise BusinessRuleError(
                f"El estudio ya está {estudio.estado.value}: no hay nada más para pagar.",
                code="estudio_ya_pago",
            )
        if estudio.estado != EstadoEstudio.CREADO:
            raise BusinessRuleError(
                f"El estudio está {estudio.estado.value}: no admite el pago particular."
            )
        if estudio.cobertura is not None:
            # [assumption] P8: after choosing or being refused by the obra social there is no
            # private payment until the business answers.
            raise BusinessRuleError(
                "El estudio tiene una cobertura por obra social: no admite el pago particular.",
                code="cobertura_en_curso",
            )

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

    @classmethod
    def _salida(cls, estudio: EstudioParaPresupuesto) -> EstudioDelPacienteSalida:
        cobertura = estudio.cobertura
        return EstudioDelPacienteSalida(
            id=estudio.id,
            estado=estudio.estado,
            cantidad_genes=len(estudio.genes),
            importe_usd=estudio.presupuesto_importe_usd,
            cupon_aplicado=None
            if estudio.cupon_aplicado is None
            else cls._cupon_salida(estudio, estudio.cupon_aplicado),
            cobertura=None
            if cobertura is None
            else CoberturaSalida(
                obra_social=cobertura.obra_social,
                porcentaje=cobertura.porcentaje,
                estado=cobertura.estado,
                motivo_rechazo=cobertura.motivo_rechazo,
                demanda_enviada=cobertura.tiene_demanda,
                demanda_nombre=cobertura.demanda_nombre,
            ),
        )
