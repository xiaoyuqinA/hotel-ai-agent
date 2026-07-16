"""Unified agent registry — central module lookup for all hotel agents."""

from __future__ import annotations

from typing import Callable, Dict, List

from agents import Agent

Factory = Callable[[], Agent]

_REGISTRY: Dict[str, Factory] = {}


def register_agent(name: str, factory: Factory) -> None:
    """Register an agent factory function.

    Args:
        name: Unique agent identifier (e.g. "guest_experience_agent").
        factory: Zero-argument callable that returns a new Agent instance.
    """
    if name in _REGISTRY:
        raise ValueError(f"Agent '{name}' is already registered.")
    _REGISTRY[name] = factory


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