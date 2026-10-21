from fastapi import APIRouter

# M8. Bioinformática y resultados
router = APIRouter(prefix="/bioinformatica", tags=["bioinformatica"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "bioinformatica"}
