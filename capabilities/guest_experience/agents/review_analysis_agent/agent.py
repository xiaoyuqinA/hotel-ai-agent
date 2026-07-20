"""Review Analysis Agent — factory + auto-registration."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from agents import Agent

from shared.llm.factory import create_agent_model
from shared.prompts.loader import load_prompt_from_agent_dir
from shared.registry.agent_registry import register_agent
from .schemas import ReviewAnalysisResult


def load_config() -> dict:
    """加载本 agent 的 config.yaml。"""
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_agent() -> Agent:
    """Create and return a Review Analysis Agent instance."""
    load_dotenv(Path(__file__).resolve().parent / ".env")

    config = load_config()
    model = create_agent_model()

    instructions = load_prompt_from_agent_dir(Path(__file__).resolve().parent)

    return Agent(
        name=os.environ.get("AGENT_NAME", config.get("name", "review_analysis_agent")) or "review_analysis_agent",
        instructions=instructions,
        model=model,
        output_type=ReviewAnalysisResult,
    )


# Auto-register on module import
register_agent(
    "review_analysis_agent",
    create_agent,
    metadata={"welcome_message": load_config().get("ui", {}).get("welcome_message", "")},
)