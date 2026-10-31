"""Proveedores de modelos de lenguaje con plan gratuito, y el cooldown de los que se agotan."""

import logging
import re
import threading
import time
from typing import Literal, Protocol

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.knowledge import Document
from app.prompt import JSON_REMINDER, Reply, build_prompt

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 600
# Los modelos que razonan (GPT-OSS) gastan parte del cupo pensando antes de responder
OPENAI_COMPATIBLE_MAX_TOKENS = 1500
TEMPERATURE = 0.6
MAX_RETRY_AFTER_SECONDS = 600

FailureKind = Literal["quota", "unavailable", "invalid"]


class ProviderError(Exception):
    """Falla de un proveedor. `kind` decide si se lo saltea un tiempo (cooldown)."""

    def __init__(
        self, provider: str, kind: FailureKind, detail: str, retry_after: int | None = None
    ):
        super().__init__(f"{provider}: {kind}: {detail}")
        self.provider = provider
        self.kind = kind
        self.retry_after = retry_after


class NoProviderAvailable(Exception):
    """Ningún proveedor de la cadena pudo responder: hay que usar el modo reglas."""


class Provider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def generate(self, question: str, history: list[dict], documents: list[Document]) -> Reply: ...


class ProviderCooldown:
    """Recuerda hasta cuándo hay que saltear a cada proveedor. Vive en memoria."""

    def __init__(self):
        self._down_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def mark_down(self, name: str, seconds: float) -> None:
        with self._lock:
            self._down_until[name] = time.monotonic() + seconds

    def is_down(self, name: str) -> bool:
        with self._lock:
            until = self._down_until.get(name)
            if until is None:
                return False
            if time.monotonic() >= until:
                del self._down_until[name]
                return False
            return True

    def reset(self) -> None:
        with self._lock:
            self._down_until.clear()


cooldown = ProviderCooldown()


def parse_reply(provider: str, text: str) -> Reply:
    """Convierte el texto del modelo en un `Reply`. Tolera bloques de código y texto alrededor."""
    candidate = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    try:
        try:
            return Reply.model_validate_json(candidate)
        except ValidationError:
            start, end = candidate.find("{"), candidate.rfind("}")
            if start == -1 or end <= start:
                raise
            return Reply.model_validate_json(candidate[start : end + 1])
    except ValidationError as exc:
        raise ProviderError(provider, "invalid", "the answer is not a valid reply") from exc


def _retry_after(response: httpx.Response) -> int | None:
    value = response.headers.get("retry-after", "")
    if value.isdigit():
        return min(int(value), MAX_RETRY_AFTER_SECONDS)
    return None


class GeminiProvider:
    """Gemini con salida estructurada (`response_schema`)."""

    name = "gemini"

    def __init__(self, settings: Settings):
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.gemini_api_key and self._settings.gemini_model)

    def generate(self, question: str, history: list[dict], documents: list[Document]) -> Reply:
        from google import genai
        from google.genai import errors, types

        settings = self._settings
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.chatbot_llm_timeout_seconds * 1000)  # milisegundos
            ),
        )
        contents = [
            types.Content(
                role="model" if turn["role"] == "assistant" else "user",
                parts=[types.Part(text=turn["content"])],
            )
            for turn in [*history, {"role": "user", "content": question}]
        ]
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=build_prompt(documents),
                    response_mime_type="application/json",
                    response_schema=Reply,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    # Algo de variedad para que las respuestas no salgan calcadas
                    temperature=TEMPERATURE,
                    # Sin "pensar": para esta tarea no hace falta
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except errors.APIError as exc:
            kind: FailureKind = "quota" if exc.code in (429, 402) else "unavailable"
            raise ProviderError(self.name, kind, f"HTTP {exc.code}") from exc
        except Exception as exc:  # timeout, red caída
            raise ProviderError(self.name, "unavailable", type(exc).__name__) from exc
        return parse_reply(self.name, response.text or "")


class OpenAICompatibleProvider:
    """Cualquier servicio que acepte el formato de OpenAI (Groq, NVIDIA NIM, OpenRouter)."""

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        json_mode: bool = True,
    ):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        # No todos los servicios aceptan `response_format`: sin él se pide el JSON en el prompt
        self._json_mode = json_mode

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model and self._base_url)

    def generate(self, question: str, history: list[dict], documents: list[Document]) -> Reply:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": f"{build_prompt(documents)}\n\n{JSON_REMINDER}"},
                *({"role": turn["role"], "content": turn["content"]} for turn in history),
                {"role": "user", "content": question},
            ],
            "temperature": TEMPERATURE,
            "max_tokens": OPENAI_COMPATIBLE_MAX_TOKENS,
        }
        if self._json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:  # timeout, red caída
            raise ProviderError(self.name, "unavailable", type(exc).__name__) from exc

        if response.status_code in (429, 402):
            raise ProviderError(
                self.name, "quota", f"HTTP {response.status_code}", _retry_after(response)
            )
        if response.status_code >= 400:
            raise ProviderError(self.name, "unavailable", f"HTTP {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(self.name, "invalid", "unexpected response shape") from exc
        return parse_reply(self.name, content or "")


def build_provider(name: str, settings: Settings) -> Provider | None:
    """Arma el proveedor con ese nombre, o None si el nombre no se conoce."""
    timeout = settings.chatbot_llm_timeout_seconds
    if name == "gemini":
        return GeminiProvider(settings)
    if name == "groq":
        return OpenAICompatibleProvider(
            "groq", settings.groq_base_url, settings.groq_api_key, settings.groq_model, timeout
        )
    if name == "nvidia":
        # NIM no documenta `response_format`: el JSON se pide en el prompt
        return OpenAICompatibleProvider(
            "nvidia",
            settings.nvidia_base_url,
            settings.nvidia_api_key,
            settings.nvidia_model,
            timeout,
            json_mode=False,
        )
    if name == "openrouter":
        return OpenAICompatibleProvider(
            "openrouter",
            settings.openrouter_base_url,
            settings.openrouter_api_key,
            settings.openrouter_model,
            timeout,
        )
    return None


def provider_chain() -> list[Provider]:
    """Los proveedores configurados (con clave), en el orden de CHATBOT_LLM_PROVIDERS."""
    settings = get_settings()
    chain: list[Provider] = []
    for name in settings.llm_providers_list:
        provider = build_provider(name, settings)
        if provider is None:
            logger.warning("Unknown provider in CHATBOT_LLM_PROVIDERS: %s", name)
        elif provider.is_configured() and provider.name not in {p.name for p in chain}:
            chain.append(provider)
    return chain


def _log_failure(exc: ProviderError) -> None:
    logger.warning("Provider failed (%s): %s", exc.kind, exc)


def generate_with_fallback(question: str, history: list[dict], documents: list[Document]) -> Reply:
    """Prueba cada proveedor en orden y devuelve la primera respuesta válida.

    Un proveedor sin cuota o caído se saltea durante el cooldown. Si ninguno responde,
    levanta `NoProviderAvailable` para que el servicio use el modo reglas.
    """
    settings = get_settings()
    for provider in provider_chain():
        if cooldown.is_down(provider.name):
            logger.info("Skipping %s: cooling down", provider.name)
            continue
        try:
            return provider.generate(question, history, documents).with_provider(provider.name)
        except ProviderError as exc:
            _log_failure(exc)
            if exc.kind in ("quota", "unavailable"):
                seconds = exc.retry_after or settings.chatbot_provider_cooldown_seconds
                cooldown.mark_down(provider.name, seconds)
        except Exception:
            logger.exception("Unexpected failure in provider %s", provider.name)
            cooldown.mark_down(provider.name, settings.chatbot_provider_cooldown_seconds)
    raise NoProviderAvailable("no language model provider could answer")
