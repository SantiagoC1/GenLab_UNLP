from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BusinessRuleError(Exception):
    """Una regla del dominio impide la operación (se responde 409 por defecto)."""

    status_code = 409
    # Opcional: le permite al frontend distinguir casos sin leer el mensaje.
    code: str | None = None

    def __init__(self, message: str, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class InvalidIntegration(BusinessRuleError):
    """Un módulo externo no responde (M10-RF3). No se pierde el trabajo ya cargado."""

    status_code = 503

    def __init__(self, integration: str):
        super().__init__(f"El módulo externo '{integration}' no está disponible.")
        self.integration = integration


class Unauthenticated(BusinessRuleError):
    """No se pudo identificar al usuario (credenciales o código incorrectos)."""

    status_code = 401


class InvalidSession(Unauthenticated):
    """Token ausente, inválido o vencido. El frontend termina la sesión cuando recibe esto."""

    code = "invalid_session"


class Forbidden(BusinessRuleError):
    """El usuario está identificado, pero no puede hacer esta acción."""

    status_code = 403


class MustChangePassword(Forbidden):
    """M1-RF7: hasta que se cambie la contraseña inicial, no se puede usar nada más."""

    code = "must_change_password"


class TooManyRequests(BusinessRuleError):
    """
    Se pidió lo mismo demasiadas veces seguidas (por ejemplo, otro código por mail).

    REUTILIZABLE: cualquier módulo que limite la frecuencia de una acción.
    """

    status_code = 429


class AccountBlocked(BusinessRuleError):
    """
    La cuenta está bloqueada por demasiados intentos fallidos de ingreso.
    """

    status_code = 423


def register_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores de negocio y de validación en la app.

    Todas las respuestas de error usan la clave `detalle` (el frontend la lee así).
    """

    @app.exception_handler(BusinessRuleError)
    async def _business_rule_error(_: Request, exc: BusinessRuleError) -> JSONResponse:
        content = {"detalle": exc.message}
        if exc.code:
            content["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def _invalid_data(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in e["loc"][1:]), "message": e["msg"]}
            for e in exc.errors()
        ]
        content = {"detalle": "Revisá los datos ingresados.", "errors": errors}
        return JSONResponse(status_code=422, content=content)
