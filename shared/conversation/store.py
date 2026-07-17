"""Session store protocol — abstracts session persistence backends."""

from typing import Protocol

from shared.conversation.session import InMemorySession


class SessionStore(Protocol):
    """Abstract session store. Implement for memory, Redis, etc."""

    def get(self, session_id: str) -> InMemorySession | None:
        """Retrieve a session by ID."""
        ...

    def create(self, session_id: str) -> InMemorySession:
        """Create and persist a new session."""
        ...

    def delete(self, session_id: str) -> None:
        """Delete a session."""
        ...


class MemorySessionStore:
    """In-memory session store — default for development."""

    def __init__(self) -> None:
        self._sessions: dict[str, InMemorySession] = {}

    def get(self, session_id: str) -> InMemorySession | None:
        return self._sessions.get(session_id)

    def create(self, session_id: str) -> InMemorySession:
        session = InMemorySession()
        self._sessions[session_id] = session
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)