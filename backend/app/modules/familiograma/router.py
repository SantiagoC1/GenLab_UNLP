from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.core.validation import raise_if_invalid
from app.modules.familiograma import service
from app.modules.familiograma.schemas import (
    FamilyTreeOut,
    KinshipOut,
    RelativeOut,
    RelativesData,
)
from app.modules.familiograma.validate import validate_relatives

router = APIRouter(prefix="/familiograma", tags=["familiograma"])

DOCTOR_ONLY = require_role(Rol.MEDICO_TRATANTE)


@router.get("/kinships", response_model=list[KinshipOut])
def list_kinships(_doctor: dict = Depends(DOCTOR_ONLY)):
    """Parentescos del módulo de familiograma, sin el del paciente."""
    return service.list_kinships()


@router.get("/patients/{patient_id}/relatives", response_model=list[RelativeOut])
def get_relatives(patient_id: str, _doctor: dict = Depends(DOCTOR_ONLY)):
    """Familiares guardados del paciente."""
    return service.get_relatives(patient_id)


@router.put("/patients/{patient_id}/relatives", response_model=list[RelativeOut])
def save_relatives(patient_id: str, body: RelativesData, _doctor: dict = Depends(DOCTOR_ONLY)):
    """Reemplaza los familiares del paciente.

    `model_dump()` convierte el modelo de Pydantic en un diccionario
    común.
    """
    data = body.model_dump()
    raise_if_invalid(validate_relatives(data))
    return service.save_relatives(patient_id, data)


@router.get("/patients/{patient_id}/family-tree", response_model=FamilyTreeOut)
def get_family_tree(patient_id: str, _doctor: dict = Depends(DOCTOR_ONLY)):
    """Genera el familiograma del paciente con sus familiares guardados."""
    return service.generate_family_tree(patient_id)
