"""Conversation manager — session lifecycle managed by a SessionStore."""

from shared.conversation.session import InMemorySession
from shared.conversation.store import MemorySessionStore, SessionStore


class ConversationManager:
    """Manages conversation sessions backed by a SessionStore.

    Callers pass a session_id; the manager handles get-or-create lifecycle.
    """

    def __init__(self, store: SessionStore | None = None) -> None:
        self._store = store or MemorySessionStore()

    def get_or_create(self, session_id: str) -> InMemorySession:
        session = self._store.get(session_id)
        if session is None:
            session = self._store.create(session_id)
        return session

    def clear(self, session_id: str) -> None:
        self._store.delete(session_id)