from datetime import UTC, datetime

from postgrest.exceptions import APIError

from app.database import supabase_admin

UNIQUE_VIOLATION = "23505"


class DniTaken(Exception):
    """Ya hay un paciente con ese DNI (la columna `dni` es única)."""


def _table(name: str):
    """Devuelve la tabla del cliente admin.

    Existe para no repetir `supabase_admin.table`.
    """
    return supabase_admin.table(name)


def find_by_dni(dni: str) -> dict | None:
    """Devuelve el paciente con ese DNI, o None.

    Pide solo las columnas mínimas para que el resumen clínico no salga
    de la base.
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


def find_by_id(patient_id: str) -> dict | None:
    """Devuelve el paciente con ese id, o None.

    Mismas columnas mínimas que `find_by_dni`.
    """
    rows = (
        _table("patients")
        .select("id, dni, first_name, last_name, birth_date")
        .eq("id", patient_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def create(row: dict, pathology_ids: list[int], symptoms: list[dict]) -> dict:
    """Guarda el paciente con sus diagnósticos presuntivos y sus síntomas.

    Si fallan los vínculos borra el paciente; los vínculos caen en
    cascada.
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
    """Borra el paciente.

    Sus diagnósticos y síntomas se borran en cascada.
    """
    _table("patients").delete().eq("id", patient_id).execute()


def create_study(row: dict, pathology_ids: list[int], genes: list[dict]) -> dict:
    """Guarda el estudio con sus patologías, genes e historial.

    Si falla un paso, borra el estudio; lo demás cae en cascada.
    """
    study = _table("studies").insert(row).execute().data[0]
    try:
        pathology_rows = [
            {"study_id": study["id"], "pathology_id": pathology_id}
            for pathology_id in pathology_ids
        ]
        _table("study_pathologies").insert(pathology_rows).execute()
        gene_rows = [
            {"study_id": study["id"], "gene": gene["gene"], "origin": gene["origin"]}
            for gene in genes
        ]
        _table("study_genes").insert(gene_rows).execute()
        history = {
            "study_id": study["id"],
            "from_state": None,
            "to_state": study["state"],
            "changed_by": row["requested_by"],
        }
        _table("study_state_history").insert(history).execute()
    except Exception:
        _table("studies").delete().eq("id", study["id"]).execute()
        raise
    return study


STUDY_COLUMNS = (
    "id, state, pompe_urgent, created_at, state_changed_at, "
    "patients!inner(first_name, last_name, dni, account_user_id), "
    "study_pathologies(pathologies(name)), study_genes(count)"
)


def list_studies_requested_by(doctor_id: str) -> list[dict]:
    """Los estudios que pidió ese médico, del más nuevo al más viejo."""
    return (
        _table("studies")
        .select(STUDY_COLUMNS)
        .eq("requested_by", doctor_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def list_studies_of_account(account_id: str) -> list[dict]:
    """Los estudios de los pacientes que cuelgan de esa cuenta.

    Incluye los de los hijos menores, que usan la cuenta de sus padres.
    """
    return (
        _table("studies")
        .select(STUDY_COLUMNS)
        .eq("patients.account_user_id", account_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def find_study(study_id: int) -> dict | None:
    """El estudio con ese id, o None si no existe."""
    rows = _table("studies").select("id, state").eq("id", study_id).execute().data
    return rows[0] if rows else None


def change_study_state(
    study_id: int, from_state: str, to_state: str, changed_by: str | None
) -> dict | None:
    """Cambia el estado del estudio y lo anota en el historial.

    Solo actualiza si el estudio sigue en `from_state`: si otro pedido
    lo cambió antes, no toca nada y devuelve None.
    """
    rows = (
        _table("studies")
        .update({"state": to_state, "state_changed_at": datetime.now(UTC).isoformat()})
        .eq("id", study_id)
        .eq("state", from_state)
        .execute()
        .data
    )
    if not rows:
        return None
    history = {
        "study_id": study_id,
        "from_state": from_state,
        "to_state": to_state,
        "changed_by": changed_by,
    }
    _table("study_state_history").insert(history).execute()
    return rows[0]
