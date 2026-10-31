"""Caché de respuestas del modelo para consultas repetidas, así se gasta menos cuota."""

import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from app.config import get_settings
from app.scope import Kind
from app.text import normalize

# Una derivación al médico puede reflejar el caso personal de quien preguntó: no se reutiliza
CACHEABLE_KINDS = frozenset({Kind.ANSWER, Kind.OUT_OF_SCOPE, Kind.NO_INFORMATION})


@dataclass(frozen=True)
class CachedAnswer:
    text: str
    kind: Kind


def cache_key(question: str) -> str:
    """Minúsculas, sin tildes ni signos y con los espacios colapsados."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", normalize(question))).strip()


class ResponseCache:
    """Guarda las últimas respuestas por texto de consulta, con vencimiento y tamaño máximo."""

    def __init__(self):
        self._entries: OrderedDict[str, tuple[float, CachedAnswer]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, question: str) -> CachedAnswer | None:
        key = cache_key(question)
        ttl = get_settings().chatbot_cache_ttl_minutes * 60
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            stored_at, answer = entry
            if time.monotonic() - stored_at > ttl:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return answer

    def put(self, question: str, text: str, kind: Kind) -> None:
        key = cache_key(question)
        limit = get_settings().chatbot_cache_max_entries
        if kind not in CACHEABLE_KINDS or not key or limit <= 0:
            return
        with self._lock:
            self._entries[key] = (time.monotonic(), CachedAnswer(text, kind))
            self._entries.move_to_end(key)
            while len(self._entries) > limit:
                self._entries.popitem(last=False)


cache = ResponseCache()
