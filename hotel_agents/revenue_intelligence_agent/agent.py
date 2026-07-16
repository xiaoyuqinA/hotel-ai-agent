"""Revenue Intelligence Agent — skeleton."""

from agents import Agent

from shared.registry.agent_registry import register_agent


def create_agent() -> Agent:
    """Create and return a Revenue Intelligence Agent instance."""
    return Agent(
        name="revenue_intelligence_agent",
        instructions=(
            "You are a hotel revenue intelligence assistant. "
            "Help with revenue analysis, pricing strategy, and forecast insights."
        ),
    )


register_agent("revenue_intelligence_agent", create_agent)