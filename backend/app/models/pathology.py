
import unicodedata

from postgrest.exceptions import APIError

from app.database import supabase_admin

UNIQUE_VIOLATION = "23505"

_SELECT = "id, name, pathology_symptoms(is_cardinal, symptoms(code, term))"


class NameTaken(Exception):
    """Ya existe una patología con ese nombre (índice único sin distinguir mayúsculas)."""


def _table(name: str):
    return supabase_admin.table(name)


def _to_pathology(row: dict) -> dict:
    links = row.get("pathology_symptoms") or []
    cardinal = next((link["symptoms"] for link in links if link["is_cardinal"]), None)
    secondary = sorted(
        (link["symptoms"] for link in links if not link["is_cardinal"]),
        key=lambda symptom: symptom["term"].casefold(),
    )
    return {"id": row["id"], "name": row["name"], "cardinal": cardinal, "secondary": secondary}


def list_all() -> list[dict]:
    """Devuelve las patologías con su síntoma cardinal y sus secundarios, ordenadas por nombre."""
    rows = _table("pathologies").select(_SELECT).order("name").execute().data
    return [_to_pathology(row) for row in rows]


def find_by_id(pathology_id: int) -> dict | None:
    """Devuelve la patología con sus síntomas, o None si no existe."""
    rows = _table("pathologies").select(_SELECT).eq("id", pathology_id).limit(1).execute().data
    return _to_pathology(rows[0]) if rows else None


def normalize_name(name: str) -> str:
    """El nombre como se guarda: en forma NFC y con los espacios juntos (`"Fabry  X"` = `"Fabry X"`)."""
    return " ".join(unicodedata.normalize("NFC", name).split())


def name_key(name: str) -> str:
    """Clave para comparar nombres: ignora mayúsculas, espacios y las formas equivalentes de Unicode
    (por ejemplo `ß` y `ss`, o una letra con tilde escrita en una o en dos piezas)."""
    folded = unicodedata.normalize("NFKC", normalize_name(name)).casefold()
    return unicodedata.normalize("NFKC", folded)


def name_exists(name: str) -> bool:
    """Indica si ya hay una patología con ese nombre (M2-RF3).

    Es más estricta que el índice único de la base (`lower(name)`): todo lo que el índice rechaza,
    esta función también, así que el índice solo queda como respaldo ante una carrera."""
    rows = _table("pathologies").select("name").execute().data
    wanted = name_key(name)
    return any(name_key(row["name"]) == wanted for row in rows)


def _links(pathology_id: int, cardinal: dict, secondary: list[dict]) -> list[dict]:
    rows = [{"pathology_id": pathology_id, "symptom_code": cardinal["code"], "is_cardinal": True}]
    rows += [
        {"pathology_id": pathology_id, "symptom_code": symptom["code"], "is_cardinal": False}
        for symptom in secondary
    ]
    return rows


def _save_symptoms(cardinal: dict, secondary: list[dict]) -> None:
    # Si el síntoma ya está, se conserva su término: no se pisa lo cargado antes.
    rows = [
        {"code": symptom["code"], "term": symptom["term"]} for symptom in [cardinal, *secondary]
    ]
    _table("symptoms").upsert(rows, on_conflict="code", ignore_duplicates=True).execute()


def create(name: str, cardinal: dict, secondary: list[dict]) -> dict:
    """Guarda la patología y sus síntomas. Si falla algo, borra la patología a medio crear."""
    _save_symptoms(cardinal, secondary)
    try:
        pathology_id = _table("pathologies").insert({"name": name}).execute().data[0]["id"]
    except APIError as error:
        if error.code == UNIQUE_VIOLATION:
            raise NameTaken from None
        raise
    try:
        _table("pathology_symptoms").insert(_links(pathology_id, cardinal, secondary)).execute()
    except Exception:
        # Los vínculos se borran en cascada con la patología
        _table("pathologies").delete().eq("id", pathology_id).execute()
        raise
    return find_by_id(pathology_id)


def replace_symptoms(pathology_id: int, cardinal: dict, secondary: list[dict]) -> dict:
    """Reemplaza el cardinal y los secundarios. Si falla, intenta devolver los anteriores."""
    previous = (
        _table("pathology_symptoms")
        .select("pathology_id, symptom_code, is_cardinal")
        .eq("pathology_id", pathology_id)
        .execute()
        .data
    )
    _save_symptoms(cardinal, secondary)
    _table("pathology_symptoms").delete().eq("pathology_id", pathology_id).execute()
    try:
        _table("pathology_symptoms").insert(_links(pathology_id, cardinal, secondary)).execute()
    except Exception:
        if previous:
            _table("pathology_symptoms").insert(previous).execute()
        raise
    return find_by_id(pathology_id)
