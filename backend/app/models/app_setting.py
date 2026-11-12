"""Acceso a la tabla `app_settings` (configuración general en pares clave y valor)."""

from datetime import UTC, datetime

from app.database import supabase_admin


def get(key: str) -> str | None:
    """Devuelve el valor de esa clave, o None si no está guardada."""
    rows = supabase_admin.table("app_settings").select("value").eq("key", key).limit(1).execute()
    return rows.data[0]["value"] if rows.data else None


def save(key: str, value: str, user_id: str) -> None:
    """Guarda el valor de la clave y quién lo cambió."""
    supabase_admin.table("app_settings").upsert(
        {
            "key": key,
            "value": value,
            "updated_by": user_id,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        on_conflict="key",
    ).execute()
