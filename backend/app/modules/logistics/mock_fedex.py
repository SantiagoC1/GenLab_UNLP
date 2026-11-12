
"""Development-only FedEx pickup simulator.

No real shipments are created.
"""

import os
from datetime import date, datetime, time
from threading import Lock
from zoneinfo import ZoneInfo

from fastapi import HTTPException


TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
_lock = Lock()
_shipments: dict[int, dict] = {}


def _get_holidays() -> set[date]:
    holidays: set[date] = set()

    for value in os.getenv("FEDEX_TEST_HOLIDAYS", "").split(","):
        value = value.strip()

        if value:
            try:
                holidays.add(date.fromisoformat(value))
            except ValueError:
                raise RuntimeError(
                    "FEDEX_TEST_HOLIDAYS must contain YYYY-MM-DD dates."
                )

    return holidays


def validate_pickup_date(scheduled_at: datetime) -> None:
    local_time = scheduled_at.astimezone(TIMEZONE)
    today = datetime.now(TIMEZONE)

    if local_time <= today:
        raise HTTPException(
            400,
            "La fecha y hora deben ser futuras.",
        )

    if local_time.weekday() >= 5:
        raise HTTPException(
            400,
            "El retiro debe programarse para un día hábil.",
        )

    if local_time.date() in _get_holidays():
        raise HTTPException(
            400,
            "No se pueden programar retiros en feriados.",
        )

    if not time(9, 0) <= local_time.time() <= time(18, 0):
        raise HTTPException(
            400,
            "El horario permitido es de 9:00 a 18:00.",
        )


def schedule_pickup(
    batch_id: int,
    scheduled_at: datetime,
) -> dict:
    validate_pickup_date(scheduled_at)

    with _lock:
        if batch_id in _shipments:
            raise HTTPException(
                409,
                "Este lote ya tiene un retiro programado.",
            )


        shipment = {
            "batch_id": batch_id,
            "scheduled_pickup_at": scheduled_at.astimezone(
                TIMEZONE
            ),
            "collected_at": None,
            "status": "Programado",
            "tracking_url": (
                f"/logistics/fedex/tracking/{batch_id}"
            ),
        }

        _shipments[batch_id] = shipment

        return dict(shipment)


def get_shipment(batch_id: int) -> dict:
    with _lock:
        shipment = _shipments.get(batch_id)

        if shipment is None:
            raise HTTPException(
                404,
                "No existe un retiro programado para este lote.",
            )

        return dict(shipment)


def simulate_collection(batch_id: int) -> dict:
    """Development-only operation simulating FedEx collection."""
    with _lock:
        shipment = _shipments.get(batch_id)

        if shipment is None:
            raise HTTPException(
                404,
                "No existe un retiro programado para este lote.",
            )

        if shipment["status"] == "Retirado":
            raise HTTPException(
                409,
                "FedEx ya retiró este lote.",
            )

        shipment["status"] = "Retirado"
        shipment["collected_at"] = datetime.now(TIMEZONE)

        return dict(shipment)


def get_configured_holidays() -> list[str]:
    return sorted(
        holiday.isoformat()
        for holiday in _get_holidays()
    )