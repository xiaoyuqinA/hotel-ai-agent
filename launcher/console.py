"""Console interactive mode — CLI chat with prompt_toolkit."""

from typing import Optional

from prompt_toolkit import PromptSession

from shared.runtime.runner import stream_agent


async def console_chat(agent_name: str, welcome: Optional[str] = None) -> None:
    if welcome is None:
        welcome = f"Agent {agent_name} interactive mode (type 'exit' to quit)"
    print(welcome)

    prompt = PromptSession()
    while True:
        try:
            user_input = await prompt.prompt_async("> ")
        except (KeyboardInterrupt, EOFError):
            break
        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        print()
        async for chunk in stream_agent(agent_name, user_input):
            print(chunk, end="", flush=True)
        print()


async def run_once(agent_name: str, user_input: str) -> None:
    async for chunk in stream_agent(agent_name, user_input):
        print(chunk, end="", flush=True)
    print()