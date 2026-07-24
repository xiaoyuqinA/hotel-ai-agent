"""Agent runtime — the single execution entry point for all agents."""

from typing import AsyncGenerator, TypeVar

from pydantic import BaseModel

from shared.conversation.manager import ConversationManager
from shared.conversation.session import InMemorySession
from shared.conversation.store import SessionStore
from shared.registry.agent_registry import get_agent
from shared.runtime.adapter import RuntimeAdapter
from shared.runtime.openai_adapter import OpenAIAdapter

T = TypeVar("T", bound=BaseModel)


class AgentRuntime:
    """Unified execution entry point.

    All callers (CLI console, API routes, etc.) go through this class.
    The adapter layer isolates the underlying SDK (OpenAI Agents, Deep Agents, …).
    Session lifecycle is managed via ConversationManager when session_id is provided.
    """

    def __init__(
        self,
        adapter: RuntimeAdapter | None = None,
        store: SessionStore | None = None,
    ):
        self._adapter = adapter or OpenAIAdapter()
        self._conversation_manager = ConversationManager(store=store)

    @property
    def conversation_manager(self) -> ConversationManager:
        return self._conversation_manager

    async def run(
        self,
        agent_name: str,
        user_input: str,
        session: InMemorySession | None = None,
        session_id: str | None = None,
    ) -> str:
        """Run an agent and return final output.

        If session_id is provided, auto-manages session via ConversationManager.
        """
        if session is None and session_id is not None:
            session = self._conversation_manager.get_or_create(session_id)
        agent = get_agent(agent_name)
        return await self._adapter.run(agent, user_input, session=session)

    async def stream(
        self,
        agent_name: str,
        user_input: str,
        session: InMemorySession | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Run an agent and yield text deltas as they arrive.

        If session_id is provided, auto-manages session via ConversationManager.
        """
        if session is None and session_id is not None:
            session = self._conversation_manager.get_or_create(session_id)
        agent = get_agent(agent_name)
        async for chunk in self._adapter.stream(agent, user_input, session=session):
            yield chunk


# Module-level convenience functions — thin wrappers around the default runtime.
_default_runtime: AgentRuntime | None = None


def _runtime() -> AgentRuntime:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = AgentRuntime()
    return _default_runtime


async def run_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> str:
    """Run an agent and return final output."""
    return await _runtime().run(agent_name, user_input, session, session_id)


async def stream_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Run an agent and yield text deltas as they arrive."""
    async for chunk in _runtime().stream(agent_name, user_input, session, session_id):
        yield chunk


async def run_agent_typed(
    agent_name: str,
    user_input: str,
    output_type: type[T],
    session: InMemorySession | None = None,
    session_id: str | None = None,
) -> T:
    """Run an agent and return typed output.

    run_agent() 保持返回 str，向后兼容。
    run_agent_typed() 用于需要类型安全的调用者（workflow nodes）。
    """
    result = await run_agent(agent_name, user_input, session, session_id)
    if isinstance(result, output_type):
        return result
    return output_type.model_validate_json(result)