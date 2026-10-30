"""Acceso a la tabla `trusted_devices`: los dispositivos desde los que ya se verificó un código.

Guarda solo el hash del identificador del navegador, nunca el identificador (M1-RF8).
"""

from app.database import supabase_admin


def _devices():
    return supabase_admin.table("trusted_devices")


def exists(user_id: str, device_hash: str) -> bool:
    """Indica si ese dispositivo ya es de confianza para ese usuario."""
    response = (
        _devices()
        .select("user_id")
        .eq("user_id", user_id)
        .eq("device_hash", device_hash)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def add(user_id: str, device_hash: str) -> None:
    """Marca el dispositivo como de confianza. Si ya lo era, no hace nada."""
    _devices().upsert(
        {"user_id": user_id, "device_hash": device_hash}, on_conflict="user_id,device_hash"
    ).execute()
