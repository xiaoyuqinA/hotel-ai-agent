"""Hotel Knowledge Agent — skeleton."""

from agents import Agent

from shared.registry.agent_registry import register_agent


def create_agent() -> Agent:
    """Create and return a Hotel Knowledge Agent instance."""
    return Agent(
        name="hotel_knowledge_agent",
        instructions=(
            "You are a hotel knowledge assistant. "
            "Answer questions about hotel policies, facilities, and local information."
        ),
    )


register_agent("hotel_knowledge_agent", create_agent)