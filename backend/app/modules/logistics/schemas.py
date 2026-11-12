
from datetime import date, datetime

from pydantic import BaseModel


class RouteStopResponse(BaseModel):
    laboratory_id: int
    laboratory: str
    address: str
    province: str
    position: int
    latitude: float | None = None
    longitude: float | None = None
    picked_up_at: datetime | None = None


class DailyRouteResponse(BaseModel):
    id: int | None = None
    date: date
    province: str | None = None
    arrived_at: datetime | None = None
    stops: list[RouteStopResponse]
