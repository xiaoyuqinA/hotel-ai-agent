"""Conversation 管理器 — 多 session 的创建、获取、清除"""

from __future__ import annotations

import asyncio
from typing import Dict

from shared.conversation.session import InMemorySession


class ConversationManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, InMemorySession] = {}

    def get_or_create(self, session_id: str) -> InMemorySession:
        if session_id not in self._sessions:
            self._sessions[session_id] = InMemorySession()
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            asyncio.get_event_loop().run_until_complete(session.clear_session())