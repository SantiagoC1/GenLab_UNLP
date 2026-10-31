
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.enums import Rol
from app.core.security import require_role
from app.modules.logistics.schemas import DailyRouteResponse
from app.modules.logistics.service import get_daily_route


router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"module": "logistics"}


@router.get(
    "/daily-route",
    response_model=DailyRouteResponse,
)
def view_daily_route(
    date: date = Query(default_factory=date.today),
    current_user: dict = Depends(require_role(Rol.TRANSPORTISTA)),
) -> DailyRouteResponse:
    """Retrieve the daily route assigned to the authenticated carrier."""

    return get_daily_route(str(current_user["id"]), date)
