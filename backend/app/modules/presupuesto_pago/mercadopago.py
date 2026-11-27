"""Payment of a study through Mercado Pago (Checkout Pro).

The patient pays on the Mercado Pago site, where the installments are chosen and managed, and comes
back to the platform. The platform receives ONE approved payment: it does not keep a state per
installment. Because a development server cannot receive webhooks, the payment is looked up by
its id when the patient comes back.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import get_settings
from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.integrations.mercadopago import MercadoPagoIntegracion, PagoNoEncontrado
from app.modules.presupuesto_pago.paciente import PacienteServicio, avisar
from app.modules.presupuesto_pago.repositorio import AsientoFinanciero, EstudioParaPresupuesto
from app.modules.presupuesto_pago.schemas import (
    CheckoutSalida,
    CondicionesPagoSalida,
    ConfirmacionPagoSalida,
)

logger = logging.getLogger("genlab.mercadopago")

INTEGRACION_MERCADOPAGO = "mercadopago"
# What identifies a study in the payment: `external_reference` comes back in the payment.
REFERENCE_PREFIX = "genlab-study-"
REFERENCE_PATTERN = re.compile(rf"^{REFERENCE_PREFIX}(\d+)$")
APPROVED = "approved"
# The payment is not accredited yet, but it may be: nothing is recorded as paid.
PENDING_STATUSES = frozenset({"pending", "in_process", "authorized", "in_mediation"})
CENTS = Decimal("0.01")
# Where Mercado Pago sends the patient back (the same screen for the three results).
RETURN_PATH = "/paciente/pago-resultado"


@dataclass(frozen=True)
class MercadoPagoConfig:
    frontend_url: str
    currency_id: str
    usd_rate: Decimal
    max_installments: int

    @classmethod
    def from_settings(cls) -> "MercadoPagoConfig":
        settings = get_settings()
        return cls(
            frontend_url=settings.frontend_url,
            currency_id=settings.mercadopago_currency_id,
            usd_rate=Decimal(str(settings.mercadopago_usd_rate)),
            max_installments=settings.mercadopago_max_installments,
        )


def reference_of(study_id: int) -> str:
    return f"{REFERENCE_PREFIX}{study_id}"


class MercadoPagoServicio:
    def __init__(
        self,
        paciente: PacienteServicio,
        cliente: MercadoPagoIntegracion,
        config: MercadoPagoConfig,
    ):
        self.paciente = paciente
        self.repositorio = paciente.repositorio
        self.cliente = cliente
        self.config = config

    # --- the charge: where the patient goes to pay ------------------------------------------

    def condiciones(self, contacto: str, estudio_id: int) -> CondicionesPagoSalida:
        """What would be charged, without creating anything in Mercado Pago."""
        return self._condiciones(contacto, estudio_id)[0]

    def _condiciones(self, contacto: str, estudio_id: int) -> tuple[CondicionesPagoSalida, Decimal]:
        estudio = self.paciente.estudio_del_paciente(contacto, estudio_id)
        self.paciente.exigir_pago_posible(estudio)
        original, importe, codigo = self.paciente.preparar_cobro(estudio)
        monto = self._monto(importe)
        condiciones = CondicionesPagoSalida(
            estudio_id=estudio.id,
            importe_original_usd=original,
            importe_usd=importe,
            cupon=codigo,
            moneda=self.config.currency_id,
            importe=float(monto),
            cuotas_maximas=self.config.max_installments,
        )
        return condiciones, monto

    def crear_checkout(self, contacto: str, estudio_id: int) -> CheckoutSalida:
        condiciones, monto = self._condiciones(contacto, estudio_id)

        return_url = f"{self.config.frontend_url.rstrip('/')}{RETURN_PATH}"
        try:
            preferencia = self.cliente.create_preference(
                external_reference=reference_of(estudio_id),
                title=f"Estudio de genética {estudio_id} - GenLab",
                amount=monto,
                currency_id=self.config.currency_id,
                max_installments=self.config.max_installments,
                back_urls={"success": return_url, "pending": return_url, "failure": return_url},
            )
        except Exception as error:
            self._registrar_fallo("crear el cobro", error)
            raise InvalidIntegration(INTEGRACION_MERCADOPAGO) from None

        return CheckoutSalida(
            **condiciones.model_dump(),
            init_point=preferencia["init_point"],
            preference_id=preferencia["id"],
        )

    # --- the patient comes back: look the payment up and record it -------------------------

    def confirmar(
        self, contacto: str, payment_id: str, usuario_id: str | None = None
    ) -> ConfirmacionPagoSalida:
        pago = self._consultar(payment_id)
        estudio = self._estudio_del_pago(contacto, pago)

        # The same payment confirmed again (a reload, a second tab): nothing is repeated.
        registrado = self.repositorio.buscar_asiento_por_pago_mp(pago["id"])
        if registrado is not None:
            return self._ya_registrado(estudio, registrado, usuario_id)

        if pago["status"] != APPROVED:
            return self._sin_acreditar(estudio, pago)

        self.paciente.exigir_pago_posible(estudio)
        original, importe, codigo = self.paciente.preparar_cobro(estudio)
        esperado = self._monto(importe)
        if (
            pago["currency_id"] != self.config.currency_id
            or pago["amount"] is None
            or pago["amount"].quantize(CENTS) != esperado
        ):
            logger.warning(
                "El monto del pago %s no coincide con el del estudio %s.", pago["id"], estudio.id
            )
            raise BusinessRuleError(
                "El monto del pago no coincide con el importe del estudio: no se registró el pago.",
                code="monto_no_coincide",
            )

        ahora = datetime.now(UTC)
        if codigo is not None:
            self.paciente.informar_uso_del_cupon(codigo)
        cuotas = pago["installments"]
        valor_cuota = (
            pago["installment_amount"]
            if pago["installment_amount"] is not None
            else (esperado / cuotas).quantize(CENTS, ROUND_HALF_UP)
        )
        try:
            asiento = self.repositorio.registrar_asiento(
                estudio,
                importe,
                f"mercadopago_{pago['payment_type_id'] or 'otro'}",
                ahora,
                codigo,
                cuotas,
                float(valor_cuota),
                pago["id"],
            )
        except Exception:
            # Two confirmations at once: the other one recorded it first.
            registrado = self.repositorio.buscar_asiento_por_pago_mp(pago["id"])
            if registrado is None:
                raise
            return self._ya_registrado(estudio, registrado, usuario_id)

        estudio = self.repositorio.cambiar_estado(
            estudio.id, EstadoEstudio.PAGADO, ahora, usuario_id
        )
        avisado = avisar(
            self.paciente.avisos,
            estudio.contacto_paciente,
            f"Recibimos el pago de su estudio (USD {importe}). Ya puede sacar su turno de extracción.",
        )
        return self._aprobado(estudio, asiento, original, avisado)

    # --- helpers ---------------------------------------------------------------------------

    def _monto(self, importe_usd: int) -> Decimal:
        """The amount in the currency of the charge (the budget is in USD)."""
        return (Decimal(importe_usd) * self.config.usd_rate).quantize(CENTS, ROUND_HALF_UP)

    def _consultar(self, payment_id: str) -> dict:
        try:
            return self.cliente.get_payment(payment_id)
        except PagoNoEncontrado:
            raise BusinessRuleError(
                "Mercado Pago no tiene ese pago.", status_code=404, code="pago_inexistente"
            ) from None
        except Exception as error:
            self._registrar_fallo("consultar el pago", error)
            raise InvalidIntegration(INTEGRACION_MERCADOPAGO) from None

    def _estudio_del_pago(self, contacto: str, pago: dict) -> EstudioParaPresupuesto:
        encontrado = REFERENCE_PATTERN.match(pago.get("external_reference") or "")
        if encontrado is None:
            raise BusinessRuleError(
                "Ese pago no corresponde a ningún estudio de la plataforma.",
                code="referencia_invalida",
            )
        # Someone else's study looks the same as a missing one.
        return self.paciente.estudio_del_paciente(contacto, int(encontrado.group(1)))

    def _ya_registrado(
        self, estudio: EstudioParaPresupuesto, asiento: AsientoFinanciero, usuario_id: str | None
    ) -> ConfirmacionPagoSalida:
        actual = self.repositorio.obtener(estudio.id) or estudio
        if actual.estado == EstadoEstudio.CREADO:
            # The payment was recorded but the state did not change (it failed in between).
            actual = self.repositorio.cambiar_estado(
                actual.id, EstadoEstudio.PAGADO, asiento.fecha, usuario_id
            )
        return self._aprobado(actual, asiento, actual.presupuesto_importe_usd, avisado=False)

    def _aprobado(
        self,
        estudio: EstudioParaPresupuesto,
        asiento: AsientoFinanciero,
        original: int | None,
        avisado: bool,
    ) -> ConfirmacionPagoSalida:
        return ConfirmacionPagoSalida(
            resultado="aprobado",
            estudio_id=estudio.id,
            estado_estudio=estudio.estado,
            estado_mp=APPROVED,
            importe_original_usd=original,
            importe_usd=asiento.importe_usd,
            cupon=asiento.cupon,
            metodo=asiento.metodo,
            cuotas=asiento.cuotas,
            valor_cuota=asiento.valor_cuota,
            moneda=self.config.currency_id,
            mp_payment_id=asiento.mp_payment_id,
            pagado_en=asiento.fecha,
            paciente_avisado=avisado,
        )

    @staticmethod
    def _sin_acreditar(estudio: EstudioParaPresupuesto, pago: dict) -> ConfirmacionPagoSalida:
        # Nothing is recorded as paid: the study stays as it is and the patient can try again.
        return ConfirmacionPagoSalida(
            resultado="pendiente" if pago["status"] in PENDING_STATUSES else "rechazado",
            estudio_id=estudio.id,
            estado_estudio=estudio.estado,
            estado_mp=pago["status"],
            detalle_mp=pago["status_detail"],
            mp_payment_id=pago["id"],
        )

    @staticmethod
    def _registrar_fallo(que: str, error: Exception) -> None:
        # The message of `MercadoPagoError` has no secrets; any other error is told by its type.
        detalle = str(error) if error.__class__.__module__.endswith("mercadopago") else ""
        logger.warning("No se pudo %s en Mercado Pago (%s). %s", que, type(error).__name__, detalle)
