from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import EstadoEstudio


class EstudioPendienteSalida(BaseModel):
    id: int
    paciente: str
    cantidad_genes: int


class DetalleEstudioSalida(BaseModel):
    id: int
    paciente: str
    genes: list[str]
    cantidad_genes: int
    importe_usd: int
    presupuesto_emitido: bool


class PresupuestoEmitidoSalida(BaseModel):
    estudio_id: int
    importe_usd: int
    emitido_en: datetime
    paciente_avisado: bool


class ObraSocialSalida(BaseModel):
    nombre: str
    cobertura: int


class ElegirCoberturaEntrada(BaseModel):
    obra_social: str = Field(min_length=1, max_length=120)


class CoberturaSalida(BaseModel):
    obra_social: str
    porcentaje: int
    estado: str
    motivo_rechazo: str | None = None


class EstudioDelPacienteSalida(BaseModel):
    id: int
    estado: EstadoEstudio
    cantidad_genes: int
    importe_usd: int | None
    cobertura: CoberturaSalida | None
