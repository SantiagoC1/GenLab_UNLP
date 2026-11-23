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
