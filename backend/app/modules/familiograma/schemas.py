from pydantic import BaseModel

from app.modules.consulta_medica.schemas import SymptomData


class RelativeData(BaseModel):
    """Un familiar del paciente.

    Todo es opcional: la validación se hace a mano en validate.py. El
    diagnóstico se elige del catálogo de patologías.
    """

    kinship_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    dni: str | None = None
    sex: str | None = None
    age: float | None = None
    deceased: bool | None = None
    symptoms: list[SymptomData] | None = None
    pathology_ids: list[int] | None = None


class RelativesData(BaseModel):
    """La lista completa de familiares de un paciente.

    Reemplaza a la que había guardada; una lista vacía la borra.
    """

    relatives: list[RelativeData] | None = None


class KinshipOut(BaseModel):
    """Un parentesco del módulo de familiograma, para el selector."""

    id: int
    name: str


class RelativeOut(BaseModel):
    """Un familiar guardado, con sus diagnósticos del catálogo.

    `linked_patient_id` es el paciente que tiene el mismo DNI, si ya
    está dado de alta.
    """

    kinship_id: int
    first_name: str
    last_name: str
    dni: str | None
    linked_patient_id: str | None
    sex: str
    age: float | None
    deceased: bool
    symptoms: list[SymptomData]
    pathologies: list[dict]


class FamilyTreeOut(BaseModel):
    """El SVG del familiograma en base64 y las advertencias del módulo."""

    warnings: list[str]
    svg_base64: str
