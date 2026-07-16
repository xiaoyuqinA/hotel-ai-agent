"""Unified CLI launcher — run any registered agent from the command line."""

import argparse
import asyncio
import sys

from agents import Runner

from shared.registry.agent_registry import get_agent, list_agents


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
    return parser


async def _run(agent_name: str, user_input: str) -> None:
    agent = get_agent(agent_name)
    result = await Runner.run(agent, user_input)
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

    if not args.agent or not args.input:
        parser.error("--agent and --input are required (or use --list).")

    asyncio.run(_run(args.agent, args.input))


if __name__ == "__main__":
    main()