from fastapi import APIRouter

# M4. Presupuesto, cobertura y pago
router = APIRouter(prefix="/presupuesto_pago", tags=["presupuesto_pago"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "presupuesto_pago"}
