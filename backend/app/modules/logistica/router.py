from fastapi import APIRouter

# M7. Logística y envío a Corea
router = APIRouter(prefix="/logistica", tags=["logistica"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "logistica"}
