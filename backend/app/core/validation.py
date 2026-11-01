from app.core.errors import BusinessRuleError


# REUTILIZABLE: los routers de todos los módulos responden igual a los errores de validación.
def raise_if_invalid(errors: list[str]) -> None:
    """
    Si hay errores de validación, responde 422 con todos los mensajes juntos.
    """
    if errors:
        raise BusinessRuleError(" ".join(errors), status_code=422)
