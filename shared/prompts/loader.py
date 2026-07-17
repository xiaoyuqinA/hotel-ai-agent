"""Prompt file loader."""

from pathlib import Path


def load_prompt(path: Path) -> str:
    """Load a prompt file and return its contents as a string."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_prompt_from_agent_dir(agent_dir: Path, filename: str = "prompt.md") -> str:
    """Convenience: load prompt.md from an agent's directory."""
    return load_prompt(agent_dir / filename)