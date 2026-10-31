from app.config import get_settings
from app.knowledge import Document
from app.prompt import SYSTEM_PROMPT, Reply, build_prompt
from app.providers import generate_with_fallback, provider_chain

__all__ = ["SYSTEM_PROMPT", "Reply", "build_prompt", "extract", "generate", "llm_enabled"]


def llm_enabled() -> bool:
    """Indica si hay que usar el modelo: no está apagado y hay al menos un proveedor con clave."""
    return get_settings().chatbot_use_llm and bool(provider_chain())


def generate(question: str, history: list[dict], documents: list[Document]) -> Reply:
    """Pide a la cadena de proveedores que interprete la consulta y la responda.

    Levanta una excepción si ninguno puede (ver `providers.generate_with_fallback`).
    Recibe la base de conocimiento (son pocos textos), así el modelo puede resolver
    sinónimos, continuaciones y consultas que mezclan varios temas.
    """
    return generate_with_fallback(question, history, documents)


def extract(documents: list[Document]) -> str:
    """Respuesta sin modelo: el texto del tema más parecido, sin su título."""
    lines = [line for line in documents[0].body.splitlines() if not line.startswith("# ")]
    return "\n".join(lines).strip()
