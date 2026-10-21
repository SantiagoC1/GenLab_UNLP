from fastapi import APIRouter

# M3. Consulta médica: pacientes y estudios
router = APIRouter(prefix="/consulta_medica", tags=["consulta_medica"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "consulta_medica"}
