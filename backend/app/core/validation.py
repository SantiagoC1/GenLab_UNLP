from app.core.errors import BusinessRuleError


def raise_if_invalid(errors: list[str]) -> None:
    """
    Si hay errores de validación, responde 422 con todos los mensajes juntos.
    """
    if errors:
        raise BusinessRuleError(" ".join(errors), status_code=422)
