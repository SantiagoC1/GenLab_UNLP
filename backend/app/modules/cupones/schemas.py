from pydantic import BaseModel, Field, field_validator


class GenerarCuponesEntrada(BaseModel):
    descuento: int = Field(ge=1, le=100, description="Porcentaje de descuento")
    cantidad: int = Field(ge=1, le=100)


class CuponSalida(BaseModel):
    codigo: str
    descuento: int
    estado: str
    pdf_url: str
    qr: str | None = Field(description="Imagen del QR (data URI), vacía si el código no entra")
    medico: str | None = None
    paciente: str | None = None


class MedicoSalida(BaseModel):
    contacto: str
    nombre: str
    matricula: str


class AsignarAMedicoEntrada(BaseModel):
    contacto_medico: str = Field(min_length=1)
    codigos: list[str] = Field(min_length=1, max_length=100)

    @field_validator("codigos")
    @classmethod
    def _sin_repetidos(cls, codigos: list[str]) -> list[str]:
        if len(set(codigos)) != len(codigos):
            raise ValueError("Hay cupones repetidos.")
        return codigos


class AsignacionSalida(BaseModel):
    medico: MedicoSalida
    codigos: list[str]
    medico_avisado: bool


class PacienteSalida(BaseModel):
    contacto: str
    nombre: str


class MisCuponesMedicoSalida(BaseModel):
    cantidad: int
    cupones: list[CuponSalida]


class AsignarAPacienteEntrada(BaseModel):
    contacto_paciente: str = Field(min_length=1)
    codigo: str = Field(min_length=1)


class AsignacionAPacienteSalida(BaseModel):
    paciente: PacienteSalida
    cupon: CuponSalida
    disponibles: int
    paciente_avisado: bool
