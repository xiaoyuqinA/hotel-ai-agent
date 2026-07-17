"""Runtime adapter protocol — abstracts the execution engine."""

from typing import AsyncGenerator, Protocol


class RuntimeAdapter(Protocol):
    """Execution adapter that wraps a specific agent SDK (e.g. OpenAI Agents, Deep Agents)."""

    async def run(self, agent: object, user_input: str, session: object | None = None) -> str:
        """Run an agent and return final output."""
        ...

    async def stream(
        self, agent: object, user_input: str, session: object | None = None,
    ) -> AsyncGenerator[str, None]:
        """Run an agent and yield text deltas as they arrive."""
        ...