import json
import logging
import re
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import knowledge, llm, scope
from app.cache import cache
from app.config import get_settings
from app.conversations import store
from app.providers import NoProviderAvailable
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


def _log_query(
    consumer: str, conversation_id: str, question: str, answer: str, kind: Kind, provider: str
) -> None:
    logger.info(
        json.dumps(
            {
                "consumidor": consumer,
                "conversacion_id": conversation_id,
                "tipo": kind,
                "provider": provider,
                "consulta": _scrub(question),
                "respuesta": _scrub(answer),
            },
            ensure_ascii=False,
        )
    )


def _shortcut(question: str) -> tuple[str, Kind] | None:
    """Respuesta fija a lo que las reglas resuelven del todo: no hace falta gastar cuota del modelo."""
    if scope.is_greeting(question):
        return scope.GREETING_MESSAGE, Kind.ANSWER
    if scope.is_courtesy(question):
        return scope.COURTESY_MESSAGE, Kind.ANSWER
    if scope.asks_for_diagnosis(question):
        return scope.MESSAGES[Kind.REFER_TO_DOCTOR], Kind.REFER_TO_DOCTOR
    return None


def _answer_with_rules(question: str, history: list[dict]) -> tuple[str, Kind]:
    """Responde sin modelo: reglas de alcance y la parte del texto de la base que corresponde."""
    shortcut = _shortcut(question)
    if shortcut:
        return shortcut

    documents = knowledge.load_knowledge()
    matches = knowledge.search(question, documents)
    previous = [turn["content"] for turn in history if turn["role"] == "user"]
    if not matches and previous:
        # Una continuación ("¿y cómo se hereda?") se entiende con la consulta anterior
        matches = knowledge.search(f"{previous[-1]} {question}", documents)
    if not matches:
        kind = Kind.NO_INFORMATION if scope.is_about_genetics(question) else Kind.OUT_OF_SCOPE
        return scope.MESSAGES[kind], kind
    return llm.extract([doc for doc, _ in matches[:2]], question), Kind.ANSWER


def _answer(question: str, history: list[dict], cacheable: bool) -> tuple[str, Kind, str]:
    """Decide cómo responder la consulta y devuelve (texto, tipo, quién respondió).

    Primero lo que las reglas resuelven solas (saludos, derivaciones) y la caché de consultas
    repetidas, para no gastar cuota. Después, el modelo, que interpreta y clasifica la consulta.
    Si no hay modelo o fallan todos los proveedores, se responde con reglas y con el texto de la
    base, para no dejar al paciente sin respuesta.
    """
    shortcut = _shortcut(question)
    if shortcut:
        return (*shortcut, "rules")

    # Solo el primer mensaje de una conversación: con historial la respuesta depende del contexto
    use_cache = cacheable and not history
    if use_cache and (hit := cache.get(question)):
        return hit.text, hit.kind, "cache"

    if llm.llm_enabled():
        documents = knowledge.select_for_prompt(question, history, knowledge.load_knowledge())
        try:
            reply = llm.generate(question, history, documents)
        except NoProviderAvailable:
            logger.warning("No language model provider answered; falling back to the rules")
        except Exception:
            logger.exception("Falló el modelo de lenguaje")
        else:
            text = reply.respuesta.strip()
            if use_cache:
                cache.put(question, text, reply.tipo)
            return text, reply.tipo, reply.provider or "model"
    text, kind = _answer_with_rules(question, history)
    return text, kind, "rules"


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

    stripped = request.mensaje.strip()
    question = _scrub(stripped)
    if not question:
        raise HTTPException(status_code=422, detail="La consulta no puede estar vacía.")

    conversation_id = request.conversacion_id or str(uuid.uuid4())
    # Una consulta con datos tapados no se cachea
    text, kind, provider = _answer(
        question, store.history(consumer, conversation_id), cacheable=question == stripped
    )
    store.add(consumer, conversation_id, question, text)
    _log_query(consumer, conversation_id, question, text, kind, provider)
    return ChatResponse(respuesta=text, conversacion_id=conversation_id, tipo=kind)
