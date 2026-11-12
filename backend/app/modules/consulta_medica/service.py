from app.core.errors import InvalidIntegration
from app.integrations.snomed import obtener_snomed

MAX_FIELD_LENGTH = 200


def search_symptoms(text: str, page: int = 1) -> dict:
    """Busca síntomas en SNOMED (escenario 7). Solo devuelve el código y el término."""
    try:
        result = obtener_snomed().buscar_terminos(text.strip(), page)
        # La respuesta del otro módulo no es de confianza: se copian solo los campos conocidos.
        items = [
            {
                "code": str(item["code"])[:MAX_FIELD_LENGTH],
                "term": str(item["term"])[:MAX_FIELD_LENGTH],
            }
            for item in result["items"]
        ]
        has_more = bool(result["has_more"])
    except Exception:
        # No se loguea el texto buscado ni el error: pueden traer datos del otro módulo.
        raise InvalidIntegration("SNOMED") from None
    return {"items": items, "page": page, "has_more": has_more}
