"""OTA Operations Agent — factory + auto-registration."""

import os
from pathlib import Path

import yaml
from agents import Agent

from shared.llm.factory import create_agent_model
from shared.prompts.loader import load_prompt_from_agent_dir
from shared.registry.agent_registry import register_agent


def load_config() -> dict:
    """加载本 agent 的 config.yaml。"""
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_agent() -> Agent:
    """Create and return an OTA Operations Agent instance."""
    config = load_config()
    model = create_agent_model()
    instructions = load_prompt_from_agent_dir(Path(__file__).resolve().parent)

    return Agent(
        name=os.environ.get("AGENT_NAME", config.get("name", "ota_operations_agent")) or "ota_operations_agent",
        instructions=instructions,
        model=model,
    )


# Auto-register on module import
register_agent(
    "ota_operations_agent",
    create_agent,
    metadata={"welcome_message": load_config().get("ui", {}).get("welcome_message", "")},
)