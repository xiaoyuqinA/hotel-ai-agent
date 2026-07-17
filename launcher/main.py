"""Unified CLI launcher — run any registered agent from the command line."""

import argparse
import asyncio

from agents import Runner

from shared.registry.agent_registry import get_agent, get_metadata, list_agents


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

    metadata = get_metadata(agent_name) or {}
    welcome = metadata.get(
        "welcome_message",
        f"Agent {agent_name} interactive mode (type 'exit' to quit)",
    )
    print(welcome)

    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
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