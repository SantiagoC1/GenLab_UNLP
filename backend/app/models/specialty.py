"""Acceso a la tabla `specialties` (catálogo de especialidades médicas)."""

from app.database import supabase_admin


def list_all():
    """Devuelve todas las especialidades (id y name), ordenadas por nombre."""
    response = supabase_admin.table("specialties").select("*").order("name").execute()
    return response.data
