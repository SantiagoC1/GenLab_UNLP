"""Validaciones de los datos de M3. Cada función devuelve una lista de errores:
si la lista está vacía, los datos son válidos."""

# SUPUESTOS (docs/Supuestos_y_pendientes.md, S3 y S4): la especificación pide "tres letras o más"
# y "paginación" sin más detalle. Se cuentan caracteres tras recortar los espacios, y los topes
# protegen al módulo externo de pedidos desmedidos.
MIN_SEARCH_LENGTH = 3
MAX_SEARCH_LENGTH = 100
MAX_PAGE = 100


def _has_control_characters(text: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def validate_symptom_search(text: str | None, page: str | None) -> list[str]:
    """Valida el texto a buscar y el número de página (que llega como texto de la URL)."""
    errors = []

    stripped = (text or "").strip()
    if len(stripped) < MIN_SEARCH_LENGTH:
        errors.append(f"Escribí al menos {MIN_SEARCH_LENGTH} letras para buscar un síntoma.")
    elif len(stripped) > MAX_SEARCH_LENGTH:
        errors.append(f"La búsqueda no puede tener más de {MAX_SEARCH_LENGTH} caracteres.")
    elif _has_control_characters(stripped):
        errors.append("La búsqueda tiene caracteres que no se pueden usar.")

    if page is not None:
        # isascii evita que int() acepte dígitos de otros alfabetos
        is_number = page.isascii() and page.isdigit() and len(page) <= 6
        if not is_number or not 1 <= int(page) <= MAX_PAGE:
            errors.append(f"La página tiene que ser un número entre 1 y {MAX_PAGE}.")

    return errors
