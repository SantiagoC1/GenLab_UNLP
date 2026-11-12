
"""Development-only daily route data.

This module uses fictional data and in-memory pickup records.
It must never be used as a production data source.
"""

from datetime import date, datetime, timezone
from threading import Lock


MOCK_CARRIER_ID = "development-carrier"

_pickup_records: dict[tuple[str, int], datetime] = {}
_pickup_lock = Lock()


def get_daily_route(
    carrier_id: str,
    route_date: str,
) -> dict | None:
    if carrier_id != MOCK_CARRIER_ID:
        return None

    if route_date != date.today().isoformat():
        return None

    return {
        "id": 1,
        "day": route_date,
        "province": "Buenos Aires",
        "arrived_at": None,
    }


def get_route_stops(route_id: int) -> list[dict]:
    if route_id != 1:
        return []

    route_date = date.today().isoformat()

    laboratories = [
        {
            "lab_id": 101,
            "position": 1,
            "extraction_labs": {
                "id": 101,
                "name": "Laboratorio de Extracción A",
                "address": "Calle 7 1234, La Plata",
                "province": "Buenos Aires",
                "latitude": -34.9214,
                "longitude": -57.9544,
            },
        },
        {
            "lab_id": 102,
            "position": 2,
            "extraction_labs": {
                "id": 102,
                "name": "Laboratorio de Extracción B",
                "address": "Calle 12 1500, La Plata",
                "province": "Buenos Aires",
                "latitude": -34.929,
                "longitude": -57.948,
            },
        },
        {
            "lab_id": 103,
            "position": 3,
            "extraction_labs": {
                "id": 103,
                "name": "Laboratorio de Extracción C",
                "address": "Calle 44 800, La Plata",
                "province": "Buenos Aires",
                "latitude": -34.915,
                "longitude": -57.96,
            },
        },
    ]

    with _pickup_lock:
        return [
            {
                **laboratory,
                "picked_up_at": _pickup_records.get(
                    (route_date, laboratory["lab_id"])
                ),
            }
            for laboratory in laboratories
        ]


def register_pickup(
    carrier_id: str,
    route_date: date,
    laboratory_id: int,
) -> datetime:
    """Record a complete pickup, enforcing the route stop order."""

    from fastapi import HTTPException

    route = get_daily_route(
        carrier_id,
        route_date.isoformat(),
    )

    if route is None:
        raise HTTPException(
            status_code=404,
            detail="No daily route was found for this date.",
        )

    with _pickup_lock:
        stops = sorted(
            get_route_stops_unlocked(route["id"], route_date),
            key=lambda stop: stop["position"],
        )

        target_stop = next(
            (
                stop
                for stop in stops
                if stop["lab_id"] == laboratory_id
            ),
            None,
        )

        if target_stop is None:
            raise HTTPException(
                status_code=404,
                detail="The laboratory is not part of this route.",
            )

        pickup_key = (
            route_date.isoformat(),
            laboratory_id,
        )

        if pickup_key in _pickup_records:
            raise HTTPException(
                status_code=409,
                detail="This pickup has already been completed.",
            )

        previous_pending = next(
            (
                stop
                for stop in stops
                if stop["position"] < target_stop["position"]
                and stop["picked_up_at"] is None
            ),
            None,
        )

        if previous_pending is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Previous route stops must be completed "
                    "before this pickup."
                ),
            )

        picked_up_at = datetime.now(timezone.utc)
        _pickup_records[pickup_key] = picked_up_at

        return picked_up_at


def get_route_stops_unlocked(
    route_id: int,
    route_date: date,
) -> list[dict]:
    """Return route stops without acquiring the pickup lock."""

    if route_id != 1:
        return []

    # Reuse the same laboratory definitions while avoiding
    # a nested acquisition of the non-reentrant lock.
    stops = [
        {
            "lab_id": 101,
            "position": 1,
        },
        {
            "lab_id": 102,
            "position": 2,
        },
        {
            "lab_id": 103,
            "position": 3,
        },
    ]

    return [
        {
            **stop,
            "picked_up_at": _pickup_records.get(
                (route_date.isoformat(), stop["lab_id"])
            ),
        }
        for stop in stops
    ]
