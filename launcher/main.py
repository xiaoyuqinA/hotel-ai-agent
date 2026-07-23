"""Unified CLI launcher — run any registered agent or workflow from the command line."""

import argparse
import asyncio

from launcher.console import console_chat, run_once
from shared.observability.langfuse import init_langfuse
from shared.registry.agent_registry import get_metadata, list_agents


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
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Workflow name to run (use --list-workflows to see available workflows).",
    )
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        dest="list_workflows",
        help="List all registered workflows and exit.",
    )
    return parser


def main() -> None:
    # Langfuse 初始化必须在 Agent 创建之前
    init_langfuse()

    # Trigger auto-registration of all agents
    import capabilities  # noqa: F401

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

    if args.list_workflows:
        from shared.registry.workflow_registry import list_workflows
        names = list_workflows()
        if not names:
            print("No workflows registered.")
            return
        print("Registered workflows:")
        for name in names:
            print(f"  - {name}")
        return

    if args.workflow:
        if not args.input:
            parser.error("--input is required when using --workflow.")
        from launcher.workflow import run_workflow_cli
        asyncio.run(run_workflow_cli(args.workflow, args.input))
        return

    if args.interactive:
        if not args.agent:
            parser.error("--agent is required for interactive mode.")
        metadata = get_metadata(args.agent)
        welcome = metadata.welcome_message if metadata else None
        asyncio.run(console_chat(args.agent, welcome=welcome))
        return

    if not args.agent or not args.input:
        parser.error("--agent and --input are required (or use --workflow, --list, or --list-workflows).")

    asyncio.run(run_once(args.agent, args.input))


if __name__ == "__main__":
    main()