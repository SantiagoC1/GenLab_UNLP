import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_settings

RESPUESTA_FIJA = (
    "Hola, soy el asistente del laboratorio de genética. "
    "Por ahora estoy en construcción y todavía no puedo responder tus consultas."
)

app = FastAPI(
    title="GenLab - Chatbot para el paciente",
    description="Servicio conversacional especializado en estudios genéticos (módulo adicional 8).",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_lista,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultaIn(BaseModel):
    mensaje: str = Field(min_length=1, description="Consulta del paciente, en texto.")
    conversacion_id: str | None = Field(
        default=None, description="Identificador para mantener el contexto de la conversación."
    )


class RespuestaOut(BaseModel):
    respuesta: str
    conversacion_id: str


class ErrorOut(BaseModel):
    detalle: str


def _verificar_disponible() -> None:
    if not get_settings().chatbot_disponible:
        raise HTTPException(
            status_code=503,
            detail="El chatbot no está disponible por el momento. Intentá de nuevo más tarde.",
        )


@app.get("/health", responses={503: {"model": ErrorOut}}, tags=["sistema"])
def health() -> dict[str, str]:
    _verificar_disponible()
    return {"estado": "ok"}


@app.post("/chat", response_model=RespuestaOut, responses={503: {"model": ErrorOut}}, tags=["chat"])
def chat(consulta: ConsultaIn) -> RespuestaOut:
    """TODO (CB3, CB4): reemplazar la respuesta fija por el modelo de lenguaje con control de alcance."""
    _verificar_disponible()
    return RespuestaOut(
        respuesta=RESPUESTA_FIJA,
        conversacion_id=consulta.conversacion_id or str(uuid.uuid4()),
    )
