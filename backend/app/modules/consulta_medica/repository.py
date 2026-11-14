"""Acceso a las tablas `patients`, `patient_pathologies` y `patient_symptoms`.

Usa el cliente admin (service role), que no pasa por RLS. El cliente no tiene transacciones: si un
paso falla, se deshacen a mano los anteriores (igual que en el repositorio de config médica).
"""

from postgrest.exceptions import APIError

from app.database import supabase_admin

UNIQUE_VIOLATION = "23505"


class DniTaken(Exception):
    """Ya hay un paciente con ese DNI (la columna `dni` es única)."""


def _table(name: str):
    """Devuelve la tabla del cliente admin. Existe para no repetir `supabase_admin.table`."""
    return supabase_admin.table(name)


def find_by_dni(dni: str) -> dict | None:
    """Devuelve el paciente con ese DNI, o None si no existe (escenario 9, M3-RF7).

    Pide solo las columnas que la búsqueda necesita: así el resumen clínico y la cuenta de acceso
    no salen de la base ni aunque alguien cambie la respuesta de la API.
    """
    rows = (
        _table("patients")
        .select("id, dni, first_name, last_name, birth_date")
        .eq("dni", dni)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def create(row: dict, pathology_ids: list[int], symptoms: list[dict]) -> dict:
    """Guarda el paciente con sus diagnósticos presuntivos y sus síntomas.

    Orden: primero los síntomas en el catálogo `symptoms` (si el código ya está, se conserva su
    término), después el paciente y por último los vínculos. Si fallan los vínculos se borra el
    paciente, y sus vínculos caen con él porque las tablas hijas tienen `on delete cascade`.
    """
    if symptoms:
        _table("symptoms").upsert(symptoms, on_conflict="code", ignore_duplicates=True).execute()

    try:
        patient = _table("patients").insert(row).execute().data[0]
    except APIError as error:
        if error.code == UNIQUE_VIOLATION:
            raise DniTaken from None
        raise

    try:
        pathology_rows = [
            {"patient_id": patient["id"], "pathology_id": pathology_id}
            for pathology_id in pathology_ids
        ]
        _table("patient_pathologies").insert(pathology_rows).execute()
        if symptoms:
            symptom_rows = [
                {"patient_id": patient["id"], "symptom_code": symptom["code"]}
                for symptom in symptoms
            ]
            _table("patient_symptoms").insert(symptom_rows).execute()
    except Exception:
        delete(patient["id"])
        raise
    return patient


def delete(patient_id: str) -> None:
    """Borra el paciente. Sus diagnósticos y síntomas se borran en cascada."""
    _table("patients").delete().eq("id", patient_id).execute()
