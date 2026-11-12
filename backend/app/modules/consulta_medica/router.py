from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.modules.consulta_medica import service
from app.modules.consulta_medica.schemas import SymptomSearchOut
from app.modules.consulta_medica.validate import validate_symptom_search

# M3. Consulta médica: pacientes y estudios
router = APIRouter(prefix="/consulta_medica", tags=["consulta_medica"])

# El gerente médico lo usa al cargar patologías (M2) y el médico tratante al cargar pacientes.
SYMPTOM_USERS = require_role(Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO)


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando todos los módulos tengan endpoints reales."""
    return {"modulo": "consulta_medica"}


@router.get("/symptoms", response_model=SymptomSearchOut)
def search_symptoms(
    q: str | None = None, page: str | None = None, _user: dict = Depends(SYMPTOM_USERS)
):
    """Escenario 7: buscador de síntomas con SNOMED. `q` y `page` se validan a mano."""
    raise_if_invalid(validate_symptom_search(q, page))
    return service.search_symptoms(q, int(page or 1))
