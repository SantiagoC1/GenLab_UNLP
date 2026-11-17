from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.modules.consulta_medica import service
from app.modules.consulta_medica.schemas import (
    PatientCreatedOut,
    PatientData,
    PatientOut,
    StudyCreatedOut,
    StudyData,
    StudyGenesOut,
    SymptomSearchOut,
)
from app.modules.consulta_medica.validate import (
    validate_dni_search,
    validate_patient,
    validate_study,
    validate_study_genes_query,
    validate_symptom_search,
)

router = APIRouter(prefix="/consulta_medica", tags=["consulta_medica"])

SYMPTOM_USERS = require_role(Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO)
DOCTOR_ONLY = require_role(Rol.MEDICO_TRATANTE)


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router.

    Se borra cuando todos los módulos tengan endpoints reales.
    """
    return {"modulo": "consulta_medica"}


@router.get("/symptoms", response_model=SymptomSearchOut)
def search_symptoms(
    q: str | None = None, page: str | None = None, _user: dict = Depends(SYMPTOM_USERS)
):
    """Buscador de síntomas con SNOMED.

    `q` y `page` se validan a mano.
    """
    raise_if_invalid(validate_symptom_search(q, page))
    return service.search_symptoms(q, int(page or 1))


@router.get("/patients", response_model=PatientOut)
def find_patient(dni: str | None = None, _doctor: dict = Depends(DOCTOR_ONLY)):
    """Busca al paciente por DNI; si no existe, responde 404."""
    raise_if_invalid(validate_dni_search(dni))
    return service.find_patient(dni)


@router.post("/patients", response_model=PatientCreatedOut, status_code=201)
def create_patient(body: PatientData, doctor: dict = Depends(DOCTOR_ONLY)):
    """Alta del paciente con su cuenta de acceso.

    `model_dump()` convierte el modelo de Pydantic en un diccionario
    común.
    """
    data = body.model_dump()
    raise_if_invalid(validate_patient(data))
    return service.create_patient(data, doctor)


@router.get("/studies/genes", response_model=StudyGenesOut)
def study_genes(
    pathology_ids: str | None = None,
    secondary_findings: str | None = None,
    _doctor: dict = Depends(DOCTOR_ONLY),
):
    """Genes de las patologías elegidas, con o sin hallazgos secundarios.

    `pathology_ids` llega como '1,2' y `secondary_findings` como 'true'
    o 'false'.
    """
    raise_if_invalid(validate_study_genes_query(pathology_ids, secondary_findings))
    ids = [int(part) for part in pathology_ids.split(",")]
    return service.get_study_genes(ids, secondary_findings == "true")


@router.post("/studies", response_model=StudyCreatedOut, status_code=201)
def create_study(body: StudyData, doctor: dict = Depends(DOCTOR_ONLY)):
    """Alta del estudio.

    `model_dump()` convierte el modelo de Pydantic en un diccionario
    común.
    """
    data = body.model_dump()
    raise_if_invalid(validate_study(data))
    return service.create_study(data, doctor)
