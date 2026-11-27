"""Fake adapters shared by the tests of the budget, coupon and appointment modules."""

from decimal import Decimal

from app.integrations.avisos import AvisosIntegracion
from app.integrations.mercadopago import (
    MercadoPagoError,
    MercadoPagoIntegracion,
    PagoNoEncontrado,
)
from app.integrations.obras_sociales import ObrasSocialesIntegracion


class AvisosEspia(AvisosIntegracion):
    """Records every notice instead of sending it."""

    def __init__(self):
        self.enviados: list[tuple[str, str, str]] = []

    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        self.enviados.append((destinatario, canal, mensaje))
        return True

    def para(self, destinatario: str) -> list[str]:
        return [m for d, _, m in self.enviados if d == destinatario]


class AvisosCaido(AvisosIntegracion):
    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        raise ConnectionError("sin servicio")


class ObrasSocialesFalsa(ObrasSocialesIntegracion):
    def __init__(self):
        self.altas: list[tuple[str, str]] = []

    def listar_obras_sociales(self) -> list[dict]:
        return [{"nombre": "OSDE", "cobertura": 80}, {"nombre": "Swiss Medical", "cobertura": 60}]

    def dar_de_alta_estudio(self, nombre: str, fecha: str) -> str:
        self.altas.append((nombre, fecha))
        return "OS-9001"

    def estado_autorizacion(self, identificador: str) -> str:
        return "Pendiente"


class MercadoPagoFalso(MercadoPagoIntegracion):
    """Mercado Pago under the control of the test: it records the charges it is asked to create
    and answers the payments the test has added."""

    def __init__(self):
        self.preferences: list[dict] = []
        self.payments: dict[str, dict] = {}
        self.queries: list[str] = []
        self.fail_create = False
        self.fail_get = False

    def create_preference(self, **kwargs) -> dict:
        if self.fail_create:
            raise MercadoPagoError("Mercado Pago respondió 500.")
        self.preferences.append(kwargs)
        number = len(self.preferences)
        return {
            "id": f"PREF-{number}",
            "init_point": f"https://www.mercadopago.com/checkout/v1/redirect?pref_id=PREF-{number}",
        }

    def get_payment(self, payment_id: str) -> dict:
        self.queries.append(payment_id)
        if self.fail_get:
            raise MercadoPagoError("Mercado Pago respondió 500.")
        if payment_id not in self.payments:
            raise PagoNoEncontrado("Mercado Pago no tiene ese pago.")
        return dict(self.payments[payment_id])

    def add_payment(
        self,
        payment_id: str = "1001",
        *,
        status: str = "approved",
        reference: str | None = "genlab-study-1",
        amount: str = "1000.00",
        currency: str = "ARS",
        installments: int = 3,
        installment_amount: str | None = "333.33",
        payment_type: str = "credit_card",
        detail: str | None = None,
    ) -> dict:
        payment = {
            "id": payment_id,
            "status": status,
            "status_detail": detail or ("accredited" if status == "approved" else status),
            "external_reference": reference,
            "amount": Decimal(amount),
            "currency_id": currency,
            "installments": installments,
            "installment_amount": None
            if installment_amount is None
            else Decimal(installment_amount),
            "payment_method_id": "visa",
            "payment_type_id": payment_type,
        }
        self.payments[payment_id] = payment
        return payment
