import threading
import time

from app.config import get_settings


class ConversationStore:
    """Guarda los últimos mensajes de cada conversación, separados por consumidor."""

    def __init__(self):
        self._conversations: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()

    def _purge(self, now: float) -> None:
        ttl = get_settings().conversation_ttl_minutes * 60
        expired = [
            key for key, value in self._conversations.items() if now - value["last_used"] > ttl
        ]
        for key in expired:
            del self._conversations[key]

    def history(self, consumer: str, conversation_id: str) -> list[dict]:
        """Devuelve los mensajes anteriores ({role, content}), o [] si la conversación es nueva."""
        with self._lock:
            self._purge(time.monotonic())
            conversation = self._conversations.get((consumer, conversation_id))
            return list(conversation["turns"]) if conversation else []

    def add(self, consumer: str, conversation_id: str, question: str, answer: str) -> None:
        """Agrega la consulta y su respuesta. Conserva solo los últimos mensajes."""
        now = time.monotonic()
        limit = get_settings().conversation_max_turns * 2
        with self._lock:
            self._purge(now)
            conversation = self._conversations.setdefault(
                (consumer, conversation_id), {"turns": [], "last_used": now}
            )
            conversation["turns"] += [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
            conversation["turns"] = conversation["turns"][-limit:]
            conversation["last_used"] = now


store = ConversationStore()
