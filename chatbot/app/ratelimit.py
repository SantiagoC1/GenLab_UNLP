"""Límite de consultas por consumidor (M11-RF9)."""

import threading
import time
from collections import defaultdict, deque

from app.config import get_settings

WINDOW_SECONDS = 60


class RateLimiter:
    """Cuenta las consultas de cada consumidor en el último minuto."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, consumer: str) -> int | None:
        """Registra una consulta. Si pasó el límite, devuelve los segundos que faltan para poder consultar."""
        now = time.monotonic()
        limit = get_settings().chatbot_rate_limit
        with self._lock:
            hits = self._hits[consumer]
            while hits and now - hits[0] >= WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(WINDOW_SECONDS - (now - hits[0])) + 1)
            hits.append(now)
            return None


limiter = RateLimiter()
