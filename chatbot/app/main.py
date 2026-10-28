import json
import logging
import re
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import knowledge, llm, scope
from app.config import get_settings
from app.conversations import store
from app.ratelimit import limiter
from app.scope import Kind

MAX_MESSAGE_LENGTH = 1000

logger = logging.getLogger("chatbot.consultas")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


app = FastAPI(
    title="GenLab - Chatbot para el paciente",
    description="Servicio conversacional especializado en estudios genéticos.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    mensaje: str = Field(
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Consulta del paciente, en texto. No incluir datos personales.",
    )
    conversacion_id: str | None = Field(
        default=None, description="Identificador para mantener el contexto de la conversación."
    )


class ChatResponse(BaseModel):
    respuesta: str
    conversacion_id: str
    tipo: Kind = Field(description="Cómo se trató la consulta: respuesta, fuera de alcance, etc.")


class ErrorResponse(BaseModel):
    detail: str


def _check_available() -> None:
    if not get_settings().chatbot_available:
        raise HTTPException(
            status_code=503,
            detail="El chatbot no está disponible por el momento. Intentá de nuevo más tarde.",
        )


def get_consumer(x_api_key: str | None = Header(default=None)):
    """Identifica al consumidor por su clave. Sin claves configuradas no se pide (desarrollo)."""
    consumers = get_settings().consumers
    if not consumers:
        return "anonimo"
    if x_api_key is None or x_api_key not in consumers:
        raise HTTPException(status_code=401, detail="Clave de API inválida.")
    return consumers[x_api_key]


def _scrub(text: str) -> str:
    """Tapa mails y números largos (DNI, teléfonos) antes de guardar la consulta (M11-RF7 y RF10)."""
    text = re.sub(r"[^\s@]+@[^\s@]+\.[^\s@]+", "[mail]", text)
    return re.sub(r"\d{6,}", "[número]", text)


def _log_query(consumer: str, conversation_id: str, question: str, answer: str, kind: Kind) -> None:
    logger.info(
        json.dumps(
            {
                "consumidor": consumer,
                "conversacion_id": conversation_id,
                "tipo": kind,
                "consulta": _scrub(question),
                "respuesta": _scrub(answer),
            },
            ensure_ascii=False,
        )
    )


def _answer_with_rules(question: str, history: list[dict]) -> tuple[str, Kind]:
    """Responde sin modelo: reglas de alcance y el texto de la base más parecido."""
    if scope.is_greeting(question):
        return scope.GREETING_MESSAGE, Kind.ANSWER
    if scope.is_courtesy(question):
        return scope.COURTESY_MESSAGE, Kind.ANSWER
    if scope.asks_for_diagnosis(question):
        return scope.MESSAGES[Kind.REFER_TO_DOCTOR], Kind.REFER_TO_DOCTOR

    documents = knowledge.load_knowledge()
    matches = knowledge.search(question, documents)
    previous = [turn["content"] for turn in history if turn["role"] == "user"]
    if not matches and previous:
        # Una continuación ("¿y cómo se hereda?") se entiende con la consulta anterior
        matches = knowledge.search(f"{previous[-1]} {question}", documents)
    if not matches:
        kind = Kind.NO_INFORMATION if scope.is_about_genetics(question) else Kind.OUT_OF_SCOPE
        return scope.MESSAGES[kind], kind
    return llm.extract([doc for doc, _ in matches[:2]]), Kind.ANSWER


def _answer(question: str, history: list[dict]) -> tuple[str, Kind]:
    """Decide cómo responder la consulta y devuelve (texto, tipo).

    Con modelo, este interpreta la consulta y la clasifica. Si no hay modelo o falla,
    se responde con reglas y con el texto de la base, para no dejar al paciente sin respuesta.
    """
    if llm.llm_enabled():
        try:
            reply = llm.generate(question, history, list(knowledge.load_knowledge()))
        except Exception:
            logger.exception("Falló el modelo de lenguaje")
        else:
            return reply.respuesta.strip(), reply.tipo
    return _answer_with_rules(question, history)


@app.get("/health", responses={503: {"model": ErrorResponse}}, tags=["sistema"])
def health():
    _check_available()
    return {"estado": "ok"}


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    tags=["chat"],
)
def chat(request: ChatRequest, consumer: str = Depends(get_consumer)) -> ChatResponse:
    """Responde una consulta sobre estudios genéticos con la base de conocimiento (CB3)."""
    _check_available()
    retry_after = limiter.check(consumer)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Demasiadas consultas. Probá de nuevo en unos segundos.",
            headers={"Retry-After": str(retry_after)},
        )

    question = _scrub(request.mensaje.strip())
    if not question:
        raise HTTPException(status_code=422, detail="La consulta no puede estar vacía.")

    conversation_id = request.conversacion_id or str(uuid.uuid4())
    text, kind = _answer(question, store.history(consumer, conversation_id))
    store.add(consumer, conversation_id, question, text)
    _log_query(consumer, conversation_id, question, text, kind)
    return ChatResponse(respuesta=text, conversacion_id=conversation_id, tipo=kind)
