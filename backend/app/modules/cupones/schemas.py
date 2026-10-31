from pydantic import BaseModel, Field


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
