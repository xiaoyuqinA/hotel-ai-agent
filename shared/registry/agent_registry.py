"""Unified agent registry — central module lookup for all hotel agents."""

from __future__ import annotations

from typing import Callable, Dict, List

from agents import Agent

Factory = Callable[[], Agent]

_REGISTRY: Dict[str, Factory] = {}
_METADATA: Dict[str, dict] = {}


def register_agent(name: str, factory: Factory, metadata: dict | None = None) -> None:
    """Register an agent factory function.

    Args:
        name: Unique agent identifier (e.g. "guest_experience_agent").
        factory: Zero-argument callable that returns a new Agent instance.
        metadata: Optional metadata dict (e.g. welcome_message) exposed to launcher.
    """
    if name in _REGISTRY:
        raise ValueError(f"Agent '{name}' is already registered.")
    _REGISTRY[name] = factory
    if metadata:
        _METADATA[name] = metadata


def get_agent(name: str) -> Agent:
    """Create a fresh Agent instance by name.

    Each call invokes the factory — instances are NOT cached.

    Raises:
        KeyError: If no agent with *name* is registered.
    """
    factory = _REGISTRY.get(name)
    if factory is None:
        raise KeyError(
            f"Agent '{name}' not registered. "
            f"Available: {list_agents()}"
        )
    return factory()


def list_agents() -> List[str]:
    """Return a sorted list of all registered agent names."""
    return sorted(_REGISTRY.keys())


def is_registered(name: str) -> bool:
    """Check whether an agent with *name* has been registered."""
    return name in _REGISTRY


def get_metadata(name: str) -> dict | None:
    """Return metadata registered for an agent, or None if unavailable."""
    return _METADATA.get(name)