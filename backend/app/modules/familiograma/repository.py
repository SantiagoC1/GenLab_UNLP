from app.database import supabase_admin

_COLUMNS = "id, kinship_id, name, last_name, sex, age, deceased, symptoms, diagnoses"


def _table(name: str):
    return supabase_admin.table(name)


def list_by_patient(patient_id: str) -> list[dict]:
    """Devuelve los familiares del paciente, en el orden en que se cargaron."""
    return (
        _table("relatives").select(_COLUMNS).eq("patient_id", patient_id).order("id").execute().data
    )


def replace_all(patient_id: str, rows: list[dict]) -> None:
    """Reemplaza los familiares del paciente por los nuevos.

    Inserta primero y borra después los anteriores, así un fallo al
    guardar no deja al paciente sin familiares.
    """
    old_ids = [relative["id"] for relative in list_by_patient(patient_id)]
    if rows:
        new_rows = [{**row, "patient_id": patient_id} for row in rows]
        _table("relatives").insert(new_rows).execute()
    if old_ids:
        _table("relatives").delete().in_("id", old_ids).execute()
