"""Marketing Content Agent — skeleton."""

from agents import Agent

from shared.registry.agent_registry import register_agent


def create_agent() -> Agent:
    """Create and return a Marketing Content Agent instance."""
    return Agent(
        name="marketing_content_agent",
        instructions=(
            "You are a hotel marketing content assistant. "
            "Help create promotional copy, social media posts, and marketing materials."
        ),
    )


register_agent("marketing_content_agent", create_agent)