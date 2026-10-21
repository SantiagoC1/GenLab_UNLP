from fastapi import APIRouter

# M1. Acceso y usuarios
router = APIRouter(prefix="/acceso", tags=["acceso"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "acceso"}
