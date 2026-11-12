from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.modules.config_medica import service
from app.modules.config_medica.schemas import (
    CdssStrategyData,
    CdssStrategyOut,
    PathologyData,
    PathologyOut,
    PathologySymptomsData,
)
from app.modules.config_medica.validate import (
    validate_cdss_strategy,
    validate_pathology,
    validate_symptoms,
)

# M2. Configuración médica
router = APIRouter(prefix="/config_medica", tags=["config_medica"])

MANAGER_ONLY = require_role(Rol.GERENTE_MEDICO)
# El médico tratante solo lee el catálogo: lo necesita para elegir el diagnóstico presuntivo (S9).
CATALOG_READERS = require_role(Rol.GERENTE_MEDICO, Rol.MEDICO_TRATANTE)


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando todos los módulos tengan endpoints reales."""
    return {"modulo": "config_medica"}


@router.get("/pathologies", response_model=list[PathologyOut])
def list_pathologies(_user: dict = Depends(CATALOG_READERS)):
    return service.list_pathologies()


@router.post("/pathologies", response_model=PathologyOut, status_code=201)
def create_pathology(data: PathologyData, _user: dict = Depends(MANAGER_ONLY)):
    """Escenario 5: alta de una patología lisosomal."""
    data = data.model_dump()
    raise_if_invalid(validate_pathology(data))
    return service.create_pathology(data)


@router.get("/cdss-strategy", response_model=CdssStrategyOut)
def get_cdss_strategy(_user: dict = Depends(MANAGER_ONLY)):
    return {"strategy": service.get_cdss_strategy()}


@router.put("/cdss-strategy", response_model=CdssStrategyOut)
def set_cdss_strategy(data: CdssStrategyData, user: dict = Depends(MANAGER_ONLY)):
    """M2-RF5: elige la estrategia que usa el CDSS."""
    data = data.model_dump()
    raise_if_invalid(validate_cdss_strategy(data))
    return {"strategy": service.set_cdss_strategy(data["strategy"], user)}


@router.put("/pathologies/{pathology_id}/symptoms", response_model=PathologyOut)
def replace_symptoms(
    pathology_id: int, data: PathologySymptomsData, _user: dict = Depends(MANAGER_ONLY)
):
    """Escenario 6: modifica el cardinal y los secundarios de una patología."""
    data = data.model_dump()
    raise_if_invalid(validate_symptoms(data))
    return service.replace_symptoms(pathology_id, data)
