import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import KNOWLEDGE_DIR
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
