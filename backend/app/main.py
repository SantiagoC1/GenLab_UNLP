from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_handlers
from app.modules.acceso.router import router as router_acceso
from app.modules.avisos.router import router as router_avisos
from app.modules.bioinformatica.router import router as router_bioinformatica
from app.modules.config_medica.router import router as router_config_medica
from app.modules.consulta_medica.router import router as router_consulta_medica
from app.modules.cupones.router import router as router_cupones
from app.modules.logistics.router import router as router_logistica
from app.modules.presupuesto_pago.router import router as router_presupuesto_pago
from app.modules.turnos.router import router as router_turnos


def create_app():
    settings = get_settings()
    app = FastAPI(title="GenLab - Plataforma del laboratorio de genética", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_lista,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_handlers(app)

    @app.get("/health", tags=["sistema"])
    def health() -> dict[str, str]:
        return {"estado": "ok"}

    app.include_router(router_acceso)
    app.include_router(router_config_medica)
    app.include_router(router_consulta_medica)
    app.include_router(router_presupuesto_pago)
    app.include_router(router_cupones)
    app.include_router(router_turnos)
    app.include_router(router_logistica)
    app.include_router(router_bioinformatica)
    app.include_router(router_avisos)
    return app


app = create_app()
