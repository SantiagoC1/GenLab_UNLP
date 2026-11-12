
"""Read-only database operations for daily routes."""

from app.database import supabase_admin


def get_daily_route(carrier_id: str, route_date: str) -> dict | None:
    if supabase_admin is None:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is required to query daily routes"
        )

    response = (
        supabase_admin.table("daily_routes")
        .select("id,day,province,arrived_at")
        .eq("carrier_id", carrier_id)
        .eq("day", route_date)
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


def get_route_stops(route_id: int) -> list[dict]:
    if supabase_admin is None:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is required to query route stops"
        )

    response = (
        supabase_admin.table("route_stops")
        .select(
            "lab_id,position,picked_up_at,"
            "extraction_labs(id,name,address,province,latitude,longitude)"
        )
        .eq("route_id", route_id)
        .order("position")
        .execute()
    )

    return response.data or []
