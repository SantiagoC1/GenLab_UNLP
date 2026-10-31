from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.core.enums import EstadoEstudio
from app.modules.turnos.reglas import ARG


class LaboratorioSalida(BaseModel):
    id: int
    nombre: str
    direccion: str
    provincia: str
    latitud: float
    longitud: float
    proximo_turno: datetime | None = None


class TurnosLibresSalida(BaseModel):
    laboratorio_id: int
    fecha: date
    turnos: list[datetime]
    motivo: str | None = None


class EstudioHabilitadoSalida(BaseModel):
    estudio_id: int
    estado: EstadoEstudio
    # Why the study can book: it is Pagado, Autorizado or has a new booking enabled.
    motivo: Literal["pagado", "autorizado", "nueva_reserva"]
    inasistencias: int = 0


class ReservarEntrada(BaseModel):
    estudio_id: int
    laboratorio_id: int
    inicio: datetime

    @field_validator("inicio")
    @classmethod
    def _con_zona_horaria(cls, inicio: datetime) -> datetime:
        # A start without a time zone is read in Argentine time.
        return inicio if inicio.tzinfo else inicio.replace(tzinfo=ARG)


class TurnoSalida(BaseModel):
    id: int
    estudio_id: int
    laboratorio: LaboratorioSalida
    inicio: datetime
    estado: str
    recordatorio_para: datetime | None
    puede_cancelar: bool
    # Published from the booking while the appointment is valid (M6-RF4).
    orden_extraccion_url: str | None = None
    consentimiento_url: str | None = None


class CancelacionSalida(BaseModel):
    turno: TurnoSalida
    estudio_estado: EstadoEstudio


class AgendaSalida(BaseModel):
    """An appointment as the extraction lab sees it."""

    turno_id: int
    estudio_id: int
    paciente: str
    laboratorio: str
    inicio: datetime
    ya_paso: bool
    inasistencias: int


class InasistenciaSalida(BaseModel):
    turno: TurnoSalida
    estudio_estado: EstadoEstudio
    inasistencias: int
    limite: int
    limite_alcanzado: bool
    paciente_avisado: bool
