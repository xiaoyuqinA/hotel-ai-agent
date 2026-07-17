"""Agent runtime — unified entry point for running agents."""

from agents import Runner

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