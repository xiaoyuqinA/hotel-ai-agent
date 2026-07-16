"""OTA Operations Agent — skeleton."""

from agents import Agent

from shared.registry.agent_registry import register_agent


def create_agent() -> Agent:
    """Create and return an OTA Operations Agent instance."""
    return Agent(
        name="ota_operations_agent",
        instructions=(
            "You are a hotel OTA operations assistant. "
            "Help manage online travel agency listings, rates, and availability."
        ),
    )


register_agent("ota_operations_agent", create_agent)