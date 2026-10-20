from fastapi import APIRouter

# M6. Turno y extracción
router = APIRouter(prefix="/turnos", tags=["turnos"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "turnos"}
