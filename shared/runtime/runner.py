"""Agent runtime — legacy compatibility layer.

This module delegates to shared/runtime/runtime.py.
New code should import from runtime.py directly.
"""

from typing import AsyncGenerator

from shared.conversation.session import InMemorySession

# Import the real implementations from runtime.py
from shared.runtime.runtime import run_agent as _run_agent
from shared.runtime.runtime import stream_agent as _stream_agent

# Re-export for backward compatibility
__all__ = ["run_agent", "stream_agent"]


async def run_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> str:
    return await _run_agent(agent_name, user_input, session, session_id)


async def stream_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_agent(agent_name, user_input, session, session_id):
        yield chunk