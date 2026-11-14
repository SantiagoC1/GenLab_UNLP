from pydantic import BaseModel


class SymptomData(BaseModel):
    """Un síntoma elegido en SNOMED: su código y su término. La validación se hace a mano."""

    code: str | None = None
    term: str | None = None


class PatientData(BaseModel):
    """Datos del alta de paciente. Todo es opcional: la validación se hace a mano en validate.py."""

    dni: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    birth_date: str | None = None
    phone: str | None = None
    email: str | None = None
    suspicion_type: str | None = None
    pathology_ids: list[int] | None = None
    clinical_summary: str | None = None
    symptoms: list[SymptomData] | None = None


class PatientOut(BaseModel):
    """Lo mínimo que se devuelve de un paciente: sin resumen clínico, mail ni cuenta de acceso."""

    id: str
    dni: str
    first_name: str
    last_name: str
    birth_date: str


class PatientCreatedOut(PatientOut):
    """Respuesta del alta: dice si se creó una cuenta nueva (y por lo tanto se enviaron credenciales)."""

    account_created: bool


class SymptomOut(BaseModel):
    code: str
    term: str


class SymptomSearchOut(BaseModel):
    items: list[SymptomOut]
    page: int
    has_more: bool
