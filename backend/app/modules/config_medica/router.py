from fastapi import APIRouter

# M2. Configuración médica
router = APIRouter(prefix="/config_medica", tags=["config_medica"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "config_medica"}
