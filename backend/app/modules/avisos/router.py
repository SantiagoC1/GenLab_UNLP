from fastapi import APIRouter

# M9. Avisos
router = APIRouter(prefix="/avisos", tags=["avisos"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "avisos"}
