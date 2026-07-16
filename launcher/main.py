"""Unified CLI launcher — run any registered agent from the command line."""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from agents import Runner

from shared.registry.agent_registry import get_agent, list_agents


def _load_welcome_message(agent_name: str) -> str:
    """从 agent 的 config.yaml 读取欢迎词，无则返回默认值。"""
    config_path = (
        Path(__file__).resolve().parents[1]
        / "hotel_agents"
        / agent_name
        / "config.yaml"
    )
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if cfg and "welcome_message" in cfg:
            return cfg["welcome_message"].strip()
    return f"Agent {agent_name} interactive mode (type 'exit' to quit)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a hotel AI agent via the unified launcher.",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Agent name to run (use --list to see available agents).",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input text to send to the agent.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_agents",
        help="List all registered agents and exit.",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enter interactive chat mode with the agent.",
    )
    return parser


async def _run(agent_name: str, user_input: str) -> None:
    agent = get_agent(agent_name)
    result = await Runner.run(agent, user_input)
    print(result.final_output)


async def _interactive_loop(agent_name: str) -> None:
    from shared.conversation.session import InMemorySession

    agent = get_agent(agent_name)
    session = InMemorySession()

    welcome = _load_welcome_message(agent_name)
    print(welcome)

    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        result = await Runner.run(agent, user_input, session=session)
        print(result.final_output)


def main() -> None:
    # Trigger auto-registration of all agents
    import hotel_agents  # noqa: F401

    parser = build_parser()
    args = parser.parse_args()

    if args.list_agents:
        names = list_agents()
        if not names:
            print("No agents registered.")
            return
        print("Registered agents:")
        for name in names:
            print(f"  - {name}")
        return

    if args.interactive:
        if not args.agent:
            parser.error("--agent is required for interactive mode.")
        asyncio.run(_interactive_loop(args.agent))
        return

    if not args.agent or not args.input:
        parser.error("--agent and --input are required (or use --list).")

    asyncio.run(_run(args.agent, args.input))


if __name__ == "__main__":
    main()