from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErrorDeNegocio(Exception):
    """Una regla del dominio impide la operación (se responde 409 por defecto)."""

    status_code = 409

    def __init__(self, mensaje: str, status_code: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if status_code is not None:
            self.status_code = status_code


class IntegracionNoDisponible(ErrorDeNegocio):
    """Un módulo externo no responde (M10-RF3). No se pierde el trabajo ya cargado."""

    status_code = 503

    def __init__(self, integracion: str):
        super().__init__(f"El módulo externo '{integracion}' no está disponible.")
        self.integracion = integracion


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def _error_de_negocio(_: Request, exc: ErrorDeNegocio) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detalle": exc.mensaje})
