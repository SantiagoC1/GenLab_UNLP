from pydantic import BaseModel


class SymptomData(BaseModel):
    """Un síntoma elegido en SNOMED: su código y su término.

    La validación se hace a mano.
    """

    code: str | None = None
    term: str | None = None


class PatientData(BaseModel):
    """Datos del alta de paciente.

    Todo es opcional: la validación se hace a mano en validate.py.
    """

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
    """Lo mínimo de un paciente: sin resumen clínico, mail ni cuenta."""

    id: str
    dni: str
    first_name: str
    last_name: str
    birth_date: str


class PatientCreatedOut(PatientOut):
    """Respuesta del alta: dice si se creó una cuenta nueva."""

    account_created: bool


class SymptomOut(BaseModel):
    code: str
    term: str


class SymptomSearchOut(BaseModel):
    items: list[SymptomOut]
    page: int
    has_more: bool


class StudyData(BaseModel):
    """Datos del alta de estudio.

    Todo es opcional: la validación se hace a mano en validate.py.
    """

    patient_id: str | None = None
    pathology_ids: list[int] | None = None
    secondary_findings: bool | None = None
    manual_genes: list[str] | None = None


class StudyGeneOut(BaseModel):
    """Un gen del estudio y su origen (patología, hallazgo o médico)."""

    gene: str
    origin: str


class GeneSearchOut(BaseModel):
    """Símbolos de genes que coinciden con lo que escribió el médico."""

    genes: list[str]


class StudyGenesOut(BaseModel):
    """Vista previa de los genes que se van a analizar."""

    genes: list[StudyGeneOut]


class StudyCreatedOut(BaseModel):
    """El estudio creado, con su estado, Pompe urgente y sus genes."""

    id: int
    state: str
    pompe_urgent: bool
    secondary_findings: bool
    genes: list[StudyGeneOut]
