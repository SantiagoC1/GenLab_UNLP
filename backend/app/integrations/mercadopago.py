"""Adaptador de Mercado Pago (Checkout Pro), el medio de pago de la plataforma.

El paciente paga en el sitio de Mercado Pago y vuelve a la plataforma. Como el servidor de
desarrollo no puede recibir avisos (webhooks), la plataforma consulta el pago por su id cuando el
paciente vuelve. Las cuotas las maneja Mercado Pago: la plataforma recibe un único pago aprobado.

El access token es un secreto del servidor: no se escribe en el código, no se registra en los logs
y no aparece en ningún mensaje de error.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.core.errors import InvalidIntegration

API_URL = "https://api.mercadopago.com"
TIMEOUT_SECONDS = 15.0


class MercadoPagoError(Exception):
    """Mercado Pago rechazó el pedido o no se pudo hablar con su API."""


class PagoNoEncontrado(MercadoPagoError):
    """Mercado Pago no tiene un pago con ese id."""


class MercadoPagoIntegracion(ABC):
    """Interfaz que usa el resto del sistema. Hay un cliente real y un simulador."""

    @abstractmethod
    def create_preference(
        self,
        *,
        external_reference: str,
        title: str,
        amount: Decimal,
        currency_id: str,
        max_installments: int,
        back_urls: dict[str, str],
    ) -> dict:
        """Crea el cobro. Devuelve `{"id": ..., "init_point": ...}`: a dónde mandar al paciente."""

    @abstractmethod
    def get_payment(self, payment_id: str) -> dict:
        """Consulta un pago por su id. Lanza `PagoNoEncontrado` si no existe.

        Devuelve `id`, `status`, `status_detail`, `external_reference`, `amount` (Decimal),
        `currency_id`, `installments`, `installment_amount` (Decimal o None),
        `payment_method_id` y `payment_type_id`.
        """


def _decimal(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def normalize_payment(data: dict) -> dict:
    """Los datos de un pago de la API, con los nombres y los tipos que usa la plataforma."""
    details = data.get("transaction_details") or {}
    return {
        "id": str(data["id"]),
        "status": data.get("status") or "",
        "status_detail": data.get("status_detail"),
        "external_reference": data.get("external_reference"),
        "amount": _decimal(data.get("transaction_amount")),
        "currency_id": data.get("currency_id"),
        "installments": int(data.get("installments") or 1),
        "installment_amount": _decimal(details.get("installment_amount")),
        "payment_method_id": data.get("payment_method_id"),
        "payment_type_id": data.get("payment_type_id"),
    }


class MercadoPagoReal(MercadoPagoIntegracion):
    """Cliente de la API de Mercado Pago (con las credenciales de prueba, el ambiente de prueba)."""

    def __init__(
        self,
        access_token: str,
        base_url: str = API_URL,
        transport: httpx.BaseTransport | None = None,
    ):
        self._access_token = access_token
        self._base_url = base_url
        self._transport = transport

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            with httpx.Client(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                return client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            # Only the kind of failure: the exception text could carry the request headers.
            raise MercadoPagoError(
                f"No se pudo hablar con Mercado Pago ({type(error).__name__})."
            ) from None

    @staticmethod
    def _failure(response: httpx.Response) -> MercadoPagoError:
        try:
            reason = response.json().get("message") or ""
        except ValueError:
            reason = ""
        return MercadoPagoError(f"Mercado Pago respondió {response.status_code}. {reason}".strip())

    def create_preference(
        self,
        *,
        external_reference: str,
        title: str,
        amount: Decimal,
        currency_id: str,
        max_installments: int,
        back_urls: dict[str, str],
    ) -> dict:
        body = {
            "items": [
                {
                    "title": title,
                    "quantity": 1,
                    "currency_id": currency_id,
                    "unit_price": float(amount),
                }
            ],
            "external_reference": external_reference,
            "back_urls": back_urls,
            # Mercado Pago sends the patient back by itself when the payment is approved.
            "auto_return": "approved",
            "payment_methods": {"installments": max_installments},
        }
        response = self._request("POST", "/checkout/preferences", json=body)
        if response.status_code not in (200, 201):
            raise self._failure(response)
        data = response.json()
        return {"id": str(data["id"]), "init_point": data["init_point"]}

    def get_payment(self, payment_id: str) -> dict:
        response = self._request("GET", f"/v1/payments/{payment_id}")
        if response.status_code == 404:
            raise PagoNoEncontrado("Mercado Pago no tiene ese pago.")
        if response.status_code != 200:
            raise self._failure(response)
        return normalize_payment(response.json())


# Pagos que creó el simulador, para poder consultarlos después.
_PAGOS: dict[str, dict] = {}


def reiniciar_simulador() -> None:
    """Borra los pagos del simulador. Lo usan los tests."""
    _PAGOS.clear()


class MercadoPagoSimulador(MercadoPagoIntegracion):
    """Aprueba el pago en cuanto se crea el cobro, para demostrar sin credenciales.

    El `init_point` lleva directo a la pantalla de vuelta de la plataforma, con los mismos datos
    que manda Mercado Pago, así el recorrido completo se puede hacer sin salir de la plataforma.
    """

    def create_preference(
        self,
        *,
        external_reference: str,
        title: str,
        amount: Decimal,
        currency_id: str,
        max_installments: int,
        back_urls: dict[str, str],
    ) -> dict:
        payment_id = f"SIM-{len(_PAGOS) + 1:06d}"
        installments = min(3, max_installments)
        _PAGOS[payment_id] = {
            "id": payment_id,
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": external_reference,
            "amount": amount,
            "currency_id": currency_id,
            "installments": installments,
            "installment_amount": (amount / installments).quantize(Decimal("0.01")),
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
        }
        init_point = (
            f"{back_urls['success']}?payment_id={payment_id}&status=approved"
            f"&external_reference={external_reference}"
        )
        return {"id": f"SIM-PREF-{payment_id}", "init_point": init_point}

    def get_payment(self, payment_id: str) -> dict:
        pago = _PAGOS.get(payment_id)
        if pago is None:
            raise PagoNoEncontrado("El simulador no tiene ese pago.")
        return dict(pago)


def obtener_mercadopago() -> MercadoPagoIntegracion:
    settings = get_settings()
    if settings.integracion_mercadopago == "real":
        if not settings.mercadopago_access_token:
            raise InvalidIntegration("mercadopago")
        return MercadoPagoReal(settings.mercadopago_access_token)
    return MercadoPagoSimulador()
