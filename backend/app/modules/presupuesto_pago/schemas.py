from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.enums import EstadoEstudio


class EstudioPendienteSalida(BaseModel):
    id: int
    paciente: str
    cantidad_genes: int


class DetalleEstudioSalida(BaseModel):
    id: int
    paciente: str
    genes: list[str]
    cantidad_genes: int
    importe_usd: int
    presupuesto_emitido: bool


class PresupuestoEmitidoSalida(BaseModel):
    estudio_id: int
    importe_usd: int
    emitido_en: datetime
    paciente_avisado: bool


class ObraSocialSalida(BaseModel):
    nombre: str
    cobertura: int


class ElegirCoberturaEntrada(BaseModel):
    obra_social: str = Field(min_length=1, max_length=120)


class CoberturaSalida(BaseModel):
    obra_social: str
    porcentaje: int
    estado: str
    motivo_rechazo: str | None = None
    demanda_enviada: bool = False
    demanda_nombre: str | None = None


class AplicarCuponEntrada(BaseModel):
    codigo: str = Field(min_length=1, max_length=64)


class CuponAplicadoSalida(BaseModel):
    codigo: str
    descuento: int
    importe_original_usd: int
    importe_con_descuento_usd: int


class EstudioDelPacienteSalida(BaseModel):
    id: int
    estado: EstadoEstudio
    cantidad_genes: int
    importe_usd: int | None
    cobertura: CoberturaSalida | None
    cupon_aplicado: CuponAplicadoSalida | None = None


class PagarEntrada(BaseModel):
    # The payment is simulated; Mercado Pago would replace these methods in the future.
    metodo: Literal["tarjeta_credito", "tarjeta_debito", "transferencia"]


class PagoSalida(BaseModel):
    estudio_id: int
    estado: EstadoEstudio
    importe_original_usd: int
    importe_usd: int
    cupon: str | None = None
    cupon_informado: bool = False
    metodo: str
    pagado_en: datetime
    paciente_avisado: bool


class CondicionesPagoSalida(BaseModel):
    """What the patient would pay through Mercado Pago, before going to pay."""

    estudio_id: int
    importe_original_usd: int
    importe_usd: int
    cupon: str | None = None
    # What Mercado Pago charges, in its currency (the budget is in USD).
    moneda: str
    importe: float
    # The installments are chosen and managed by Mercado Pago.
    cuotas_maximas: int


class CheckoutSalida(CondicionesPagoSalida):
    """Where the patient goes to pay: the checkout of Mercado Pago."""

    init_point: str
    preference_id: str


class ConfirmarPagoMercadoPagoEntrada(BaseModel):
    # The id that Mercado Pago puts in the address the patient comes back to.
    payment_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ConfirmacionPagoSalida(BaseModel):
    """What happened with the payment when the patient came back from Mercado Pago."""

    resultado: Literal["aprobado", "pendiente", "rechazado"]
    estudio_id: int
    estado_estudio: EstadoEstudio
    estado_mp: str
    detalle_mp: str | None = None
    importe_original_usd: int | None = None
    importe_usd: int | None = None
    cupon: str | None = None
    metodo: str | None = None
    cuotas: int | None = None
    valor_cuota: float | None = None
    moneda: str | None = None
    mp_payment_id: str | None = None
    pagado_en: datetime | None = None
    paciente_avisado: bool = False


class AsientoFinancieroSalida(BaseModel):
    id: int
    estudio_id: int
    paciente: str
    importe_usd: int
    metodo: str
    fecha: datetime
    cupon: str | None
    cuotas: int | None = None
    valor_cuota: float | None = None
    mp_payment_id: str | None = None


class AutorizacionPendienteSalida(BaseModel):
    estudio_id: int
    paciente: str
    obra_social: str
    porcentaje: int
    importe_usd: int
    estado_estudio: EstadoEstudio
    motivo_rechazo: str | None = None
    con_demanda: bool = False
    demanda_nombre: str | None = None


class DemandaEnviadaSalida(BaseModel):
    estudio_id: int
    estado: EstadoEstudio
    demanda_nombre: str
    administrativo_avisado: bool


class RespuestaObraSocialEntrada(BaseModel):
    resultado: Literal["Autorizado", "Rechazado"]
    motivo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _el_rechazo_lleva_motivo(self):
        if self.resultado == "Rechazado" and not (self.motivo or "").strip():
            raise ValueError("El rechazo necesita el motivo.")
        return self


class AutorizacionRegistradaSalida(BaseModel):
    estudio_id: int
    estado: EstadoEstudio
    resultado: str
    motivo: str | None
    paciente_avisado: bool
