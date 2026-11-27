"""The real client of Mercado Pago, against a simulated HTTP server (no network, no token)."""

import json
import logging
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import InvalidIntegration
from app.integrations import mercadopago
from app.integrations.mercadopago import (
    MercadoPagoError,
    MercadoPagoReal,
    MercadoPagoSimulador,
    PagoNoEncontrado,
    normalize_payment,
    obtener_mercadopago,
    reiniciar_simulador,
)

# A made-up token: it must travel as a header and nowhere else.
TOKEN = "APP_USR-0000000000000000-000000-secretsecretsecret-000000"
BACK_URLS = {
    "success": "http://localhost:5173/paciente/pago-resultado",
    "pending": "http://localhost:5173/paciente/pago-resultado",
    "failure": "http://localhost:5173/paciente/pago-resultado",
}
PAYMENT = {
    "id": 1234567,
    "status": "approved",
    "status_detail": "accredited",
    "external_reference": "genlab-study-4",
    "transaction_amount": 1000,
    "currency_id": "ARS",
    "installments": 3,
    "payment_method_id": "visa",
    "payment_type_id": "credit_card",
    "transaction_details": {"installment_amount": 333.33, "total_paid_amount": 1000},
}


def client_with(handler) -> tuple[MercadoPagoReal, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return MercadoPagoReal(TOKEN, transport=httpx.MockTransport(record)), seen


def create(client: MercadoPagoReal) -> dict:
    return client.create_preference(
        external_reference="genlab-study-4",
        title="Estudio de genética 4 - GenLab",
        amount=Decimal("1000.00"),
        currency_id="ARS",
        max_installments=6,
        back_urls=BACK_URLS,
    )


def test_the_charge_asks_for_the_installments_the_back_urls_and_the_reference():
    client, seen = client_with(
        lambda request: httpx.Response(
            201, json={"id": "PREF-1", "init_point": "https://www.mercadopago.com/checkout/PREF-1"}
        )
    )

    preference = create(client)

    assert preference == {
        "id": "PREF-1",
        "init_point": "https://www.mercadopago.com/checkout/PREF-1",
    }
    (request,) = seen
    assert (request.method, request.url.path) == ("POST", "/checkout/preferences")
    body = json.loads(request.content)
    assert body["external_reference"] == "genlab-study-4"
    assert body["payment_methods"] == {"installments": 6}
    assert body["back_urls"] == BACK_URLS
    assert body["auto_return"] == "approved"
    assert body["items"] == [
        {
            "title": "Estudio de genética 4 - GenLab",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 1000.0,
        }
    ]


def test_the_token_goes_only_in_the_authorization_header():
    client, seen = client_with(
        lambda request: httpx.Response(201, json={"id": "PREF-1", "init_point": "https://mp/x"})
    )

    create(client)

    (request,) = seen
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert TOKEN.encode() not in request.content
    assert TOKEN not in str(request.url)


def test_a_rejected_charge_is_an_error_that_does_not_show_the_token(caplog):
    client, _ = client_with(
        lambda request: httpx.Response(400, json={"message": "invalid unit_price"})
    )

    with caplog.at_level(logging.DEBUG), pytest.raises(MercadoPagoError) as error:
        create(client)

    assert "400" in str(error.value)
    assert "invalid unit_price" in str(error.value)
    assert TOKEN not in str(error.value)
    assert TOKEN not in caplog.text


def test_a_network_failure_is_an_error_that_does_not_show_the_token(caplog):
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot connect with {request.headers['Authorization']}")

    client, _ = client_with(down)

    with caplog.at_level(logging.DEBUG), pytest.raises(MercadoPagoError) as error:
        create(client)

    assert "ConnectError" in str(error.value)
    assert TOKEN not in str(error.value)
    assert TOKEN not in caplog.text


def test_a_payment_is_read_by_its_id_with_the_names_of_the_platform():
    client, seen = client_with(lambda request: httpx.Response(200, json=PAYMENT))

    payment = client.get_payment("1234567")

    assert (seen[0].method, seen[0].url.path) == ("GET", "/v1/payments/1234567")
    assert payment == {
        "id": "1234567",
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": "genlab-study-4",
        "amount": Decimal("1000"),
        "currency_id": "ARS",
        "installments": 3,
        "installment_amount": Decimal("333.33"),
        "payment_method_id": "visa",
        "payment_type_id": "credit_card",
    }


def test_a_payment_without_installment_data_is_a_single_payment():
    payment = normalize_payment({"id": 9, "status": "pending", "transaction_amount": 10.5})

    assert payment["installments"] == 1
    assert payment["installment_amount"] is None
    assert payment["amount"] == Decimal("10.5")


def test_an_unknown_payment_is_reported_as_missing():
    client, _ = client_with(lambda request: httpx.Response(404, json={"message": "not found"}))

    with pytest.raises(PagoNoEncontrado):
        client.get_payment("1")


def test_a_server_error_when_reading_a_payment_is_an_error():
    client, _ = client_with(lambda request: httpx.Response(500, json={}))

    with pytest.raises(MercadoPagoError):
        client.get_payment("1")


# --- the simulator and the choice of the client -------------------------------------------------


def test_the_simulator_approves_the_charge_and_answers_the_payment():
    reiniciar_simulador()
    simulator = MercadoPagoSimulador()

    preference = simulator.create_preference(
        external_reference="genlab-study-4",
        title="x",
        amount=Decimal("600.00"),
        currency_id="ARS",
        max_installments=6,
        back_urls=BACK_URLS,
    )

    assert preference["init_point"].startswith(BACK_URLS["success"] + "?payment_id=SIM-")
    payment_id = preference["init_point"].split("payment_id=")[1].split("&")[0]
    payment = simulator.get_payment(payment_id)
    assert (payment["status"], payment["external_reference"]) == ("approved", "genlab-study-4")
    assert payment["installments"] == 3
    assert payment["installment_amount"] == Decimal("200.00")
    with pytest.raises(PagoNoEncontrado):
        simulator.get_payment("SIM-999999")
    reiniciar_simulador()


def settings_with(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_by_default_the_simulator_is_used(monkeypatch):
    monkeypatch.setattr(mercadopago, "get_settings", lambda: settings_with())

    assert isinstance(obtener_mercadopago(), MercadoPagoSimulador)


def test_the_real_client_needs_the_token(monkeypatch):
    monkeypatch.setattr(
        mercadopago, "get_settings", lambda: settings_with(integracion_mercadopago="real")
    )

    with pytest.raises(InvalidIntegration):
        obtener_mercadopago()


def test_the_real_client_is_used_with_the_token(monkeypatch):
    monkeypatch.setattr(
        mercadopago,
        "get_settings",
        lambda: settings_with(integracion_mercadopago="real", mercadopago_access_token=TOKEN),
    )

    assert isinstance(obtener_mercadopago(), MercadoPagoReal)
