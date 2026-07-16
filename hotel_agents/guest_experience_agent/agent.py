"""Guest Experience Agent — factory + auto-registration."""

import os
from pathlib import Path

from dotenv import load_dotenv
from agents import Agent

from shared.llm.factory import create_agent_model
from shared.registry.agent_registry import register_agent


def create_agent() -> Agent:
    """Create and return a Guest Experience Agent instance."""
    load_dotenv(Path(__file__).resolve().parent / ".env")

    model = create_agent_model()

    return Agent(
        name=os.environ.get("AGENT_NAME", "guest_experience_agent"),
        instructions=(
            "You are a hotel guest experience assistant. "
            "Help guests with inquiries about rooms, amenities, "
            "bookings, and hotel services."
        ),
        model=model,
    )


# Auto-register on module import
register_agent("guest_experience_agent", create_agent)