import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import KNOWLEDGE_DIR, get_settings
from app.text import GENERIC_DOMAIN_TERMS, tokenize

TITLE_WEIGHT = 3
BODY_WEIGHT = 1
MIN_SCORE = 3


@dataclass
class Document:
    topic: str
    source: str
    status: str
    body: str
    title_tokens: set[str]
    body_tokens: set[str]


def _parse(path: Path) -> Document | None:
    """Lee un archivo con encabezado `---`. Devuelve None si no tiene encabezado."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        return None
    header = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    header = {key.strip(): value.strip() for key, value in header.items()}
    body = match.group(2).strip()
    # El título sale del tema y de las palabras clave del encabezado
    title_text = f"{header.get('tema', '')} {header.get('claves', '')}"
    return Document(
        topic=header.get("tema", path.stem),
        source=header.get("fuente", ""),
        status=header.get("estado", "borrador"),
        body=body,
        title_tokens=tokenize(title_text) - GENERIC_DOMAIN_TERMS,
        body_tokens=tokenize(body) - GENERIC_DOMAIN_TERMS,
    )


@lru_cache
def load_knowledge(directory: Path = KNOWLEDGE_DIR) -> tuple[Document, ...]:
    """Carga todos los textos de la carpeta. Ignora los que no tienen encabezado (el README)."""
    documents = [_parse(path) for path in sorted(directory.glob("*.md"))]
    return tuple(doc for doc in documents if doc is not None)


def search(question: str, documents: tuple[Document, ...]) -> list[tuple[Document, int]]:
    """Devuelve los textos que responden la consulta, del más al menos parecido.

    El puntaje suma 3 por cada palabra de la consulta que está en el tema o en las claves
    del texto, y 1 por cada una que está en el cuerpo. Solo cuentan los que llegan al mínimo.
    """
    words = tokenize(question) - GENERIC_DOMAIN_TERMS
    scored = []
    for doc in documents:
        score = sum(
            TITLE_WEIGHT if word in doc.title_tokens else BODY_WEIGHT
            for word in words
            if word in doc.title_tokens or word in doc.body_tokens
        )
        if score >= MIN_SCORE:
            scored.append((doc, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)


def select_for_prompt(
    question: str, history: list[dict], documents: tuple[Document, ...]
) -> list[Document]:
    """Elige los textos que se le pasan al modelo.

    Con una base chica van todos (el modelo resuelve sinónimos y continuaciones). Cuando la base
    supera `chatbot_prompt_max_documents`, van solo los más parecidos a la consulta (junto con la
    anterior, si es una continuación). Si el buscador no encuentra nada, van todos.
    """
    settings = get_settings()
    if len(documents) <= settings.chatbot_prompt_max_documents:
        return list(documents)
    previous = [turn["content"] for turn in history if turn["role"] == "user"]
    query = f"{previous[-1]} {question}" if previous else question
    matches = search(query, documents)
    if not matches:
        return list(documents)
    return [doc for doc, _ in matches[: settings.chatbot_prompt_top_documents]]


def _units(body: str) -> list[str]:
    """Párrafos del texto; las listas con guiones se parten en un elemento por línea."""
    units: list[str] = []
    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("- ") for line in lines):
            units.extend(line[2:] for line in lines)
        elif lines:
            text = "\n".join(lines)
            if units and units[-1].endswith(":"):
                # Una introducción ("…estas etapas:") va con la lista que presenta, no sola
                units[-1] = f"{units[-1]}\n\n{text}"
            else:
                units.append(text)
    return units


def best_fragment(question: str, document: Document) -> str:
    """Devuelve la parte del texto que responde la consulta, más su frase final.

    Las palabras que solo nombran el tema ("Pompe") no cuentan: lo que importa es lo que se pregunta
    sobre él. Cada palabra de la consulta pesa más cuanto en menos párrafos aparece. Gana el párrafo
    de mayor puntaje y, a igual puntaje, el primero. La última frase (que sugiere consultar al
    médico tratante) siempre acompaña la respuesta y no participa del puntaje. Si ningún párrafo
    comparte palabras con la consulta, o si la consulta solo nombra el tema ("¿qué es Pompe?"),
    devuelve el texto completo.
    """
    units = _units(document.body)
    if len(units) < 3:
        return "\n\n".join(units)
    closing, candidates = units[-1], units[:-1]
    words = tokenize(question) - GENERIC_DOMAIN_TERMS - tokenize(document.topic)
    if not words:
        return "\n\n".join(units)
    unit_tokens = [tokenize(unit) for unit in candidates]
    weights = {
        word: 1 / sum(word in tokens for tokens in unit_tokens)
        for word in words
        if any(word in tokens for tokens in unit_tokens)
    }
    scores = [sum(weights.get(word, 0) for word in tokens) for tokens in unit_tokens]
    if max(scores) == 0:
        return "\n\n".join(units)
    return f"{candidates[scores.index(max(scores))]}\n\n{closing}"
