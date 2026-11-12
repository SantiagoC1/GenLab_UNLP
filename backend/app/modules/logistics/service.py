
"""Business logic for carrier daily routes."""

from datetime import date
from typing import Protocol

from app.modules.logistics.schemas import (
    DailyRouteResponse,
    RouteStopResponse,
)


class DailyRouteRepository(Protocol):
    def get_daily_route(
        self,
        carrier_id: str,
        route_date: str,
    ) -> dict | None:
        ...

    def get_route_stops(self, route_id: int) -> list[dict]:
        ...


def get_daily_route(
    carrier_id: str,
    route_date: date,
    repository: DailyRouteRepository | None = None,
) -> DailyRouteResponse:
    if repository is None:
        from app.modules.logistics import repository as real_repository

        repository = real_repository

    route = repository.get_daily_route(
        carrier_id,
        route_date.isoformat(),
    )

    if route is None:
        return DailyRouteResponse(
            date=route_date,
            stops=[],
        )

    stops: list[RouteStopResponse] = []

    for record in repository.get_route_stops(route["id"]):
        laboratory = record.get("extraction_labs")

        if not laboratory:
            continue

        stops.append(
            RouteStopResponse(
                laboratory_id=record["lab_id"],
                laboratory=laboratory["name"],
                address=laboratory["address"],
                province=laboratory["province"],
                position=record["position"],
                latitude=laboratory.get("latitude"),
                longitude=laboratory.get("longitude"),
                picked_up_at=record.get("picked_up_at"),
            )
        )

    stops.sort(key=lambda stop: stop.position)

    return DailyRouteResponse(
        id=route["id"],
        date=route_date,
        province=route["province"],
        arrived_at=route.get("arrived_at"),
        stops=stops,
    )
