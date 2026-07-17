"""Agent runtime — unified entry point for running agents."""

from typing import AsyncIterator

from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent

from shared.conversation.session import InMemorySession
from shared.registry.agent_registry import get_agent


async def run_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
) -> str:
    """Run an agent and return final output."""
    agent = get_agent(agent_name)
    result = await Runner.run(agent, user_input, session=session)
    return result.final_output


async def stream_agent(
    agent_name: str,
    user_input: str,
    session: InMemorySession | None = None,
) -> AsyncIterator[str]:
    """Run an agent and yield text deltas as they arrive."""
    agent = get_agent(agent_name)
    result = Runner.run_streamed(agent, input=user_input, session=session)

    async for event in result.stream_events():
        if (
            event.type == "raw_response_event"
            and isinstance(event.data, ResponseTextDeltaEvent)
        ):
            yield event.data.delta