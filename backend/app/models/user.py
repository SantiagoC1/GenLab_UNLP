"""Acceso a la tabla `users` y a `user_specialties`.

Usa el cliente admin (service role), que no pasa por RLS. Las contraseñas no están acá:
las maneja Supabase Auth.
"""

from app.database import supabase_admin


def _users():
    return supabase_admin.table("users")


def find_by_id(user_id: str):
    """Devuelve el usuario con ese id, o None si no existe."""
    response = _users().select("*").eq("id", user_id).limit(1).execute()
    return response.data[0] if response.data else None


def find_by_email(email: str):
    """Devuelve el usuario con ese mail (sin distinguir mayúsculas), o None si no existe."""
    response = _users().select("*").eq("email", email.strip().lower()).limit(1).execute()
    return response.data[0] if response.data else None


def list_all():
    """Devuelve todos los usuarios, ordenados por apellido y nombre."""
    response = _users().select("*").order("last_name").order("first_name").execute()
    return response.data


def carrier_exists_in(province: str):
    """Indica si ya hay un transportista que cubre esa provincia (M1-RF6)."""
    response = (
        _users()
        .select("id")
        .eq("role", "transportista")
        .eq("province", province)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def create(data: dict):
    """Guarda el usuario y sus especialidades. `data["id"]` es el id de Supabase Auth.

    Si falla, el que llama borra el usuario de Auth, y eso borra también estas filas
    (la tabla `users` tiene `on delete cascade`).
    """
    row = {key: value for key, value in data.items() if key != "specialty_ids"}
    user = _users().insert(row).execute().data[0]

    specialty_ids = data.get("specialty_ids") or []
    if specialty_ids:
        rows = [
            {"user_id": user["id"], "specialty_id": specialty_id} for specialty_id in specialty_ids
        ]
        supabase_admin.table("user_specialties").insert(rows).execute()
    return user


def update(user_id: str, fields: dict):
    """Actualiza los campos indicados. Devuelve el usuario actualizado."""
    response = _users().update(fields).eq("id", user_id).execute()
    return response.data[0] if response.data else None


def delete(user_id: str):
    """Borra la fila del usuario (no el usuario de Auth)."""
    _users().delete().eq("id", user_id).execute()