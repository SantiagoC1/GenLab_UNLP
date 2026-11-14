from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.modules.consulta_medica import service
from app.modules.consulta_medica.schemas import (
    PatientCreatedOut,
    PatientData,
    PatientOut,
    SymptomSearchOut,
)
from app.modules.consulta_medica.validate import (
    validate_dni_search,
    validate_patient,
    validate_symptom_search,
)

router = APIRouter(prefix="/consulta_medica", tags=["consulta_medica"])

SYMPTOM_USERS = require_role(Rol.MEDICO_TRATANTE, Rol.GERENTE_MEDICO)
DOCTOR_ONLY = require_role(Rol.MEDICO_TRATANTE)


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando todos los módulos tengan endpoints reales."""
    return {"modulo": "consulta_medica"}


@router.get("/symptoms", response_model=SymptomSearchOut)
def search_symptoms(
    q: str | None = None, page: str | None = None, _user: dict = Depends(SYMPTOM_USERS)
):
    """Escenario 7: buscador de síntomas con SNOMED. `q` y `page` se validan a mano.

    Lo usan el gerente médico al cargar patologías (M2) y el médico tratante al cargar pacientes.
    """
    raise_if_invalid(validate_symptom_search(q, page))
    return service.search_symptoms(q, int(page or 1))


@router.get("/patients", response_model=PatientOut)
def find_patient(dni: str | None = None, _doctor: dict = Depends(DOCTOR_ONLY)):
    """Escenario 9, paso 1: busca al paciente por DNI. Si no existe responde 404."""
    raise_if_invalid(validate_dni_search(dni))
    return service.find_patient(dni)


@router.post("/patients", response_model=PatientCreatedOut, status_code=201)
def create_patient(body: PatientData, doctor: dict = Depends(DOCTOR_ONLY)):
    """Escenario 9: alta del paciente con su cuenta de acceso y el envío de credenciales.

    `model_dump()` convierte el modelo de Pydantic en un diccionario común, que es lo que reciben
    la validación y el servicio.
    """
    data = body.model_dump()
    raise_if_invalid(validate_patient(data))
    return service.create_patient(data, doctor)
