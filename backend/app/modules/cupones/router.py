from fastapi import APIRouter

# M5. Cupones de descuento
router = APIRouter(prefix="/cupones", tags=["cupones"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "cupones"}
