from datetime import datetime

from pydantic import BaseModel


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
