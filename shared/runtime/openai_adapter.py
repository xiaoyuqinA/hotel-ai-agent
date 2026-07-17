"""OpenAI Agents SDK adapter — wraps Runner.run / Runner.run_streamed."""

from typing import AsyncGenerator

from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent


class OpenAIAdapter:
    """Runtime adapter for the OpenAI Agents SDK."""

    async def run(self, agent: object, user_input: str, session: object | None = None) -> str:
        result = await Runner.run(agent, user_input, session=session)
        return result.final_output

    async def stream(
        self, agent: object, user_input: str, session: object | None = None,
    ) -> AsyncGenerator[str, None]:
        result = Runner.run_streamed(agent, input=user_input, session=session)

        async for event in result.stream_events():
            if (
                event.type == "raw_response_event"
                and isinstance(event.data, ResponseTextDeltaEvent)
            ):
                yield event.data.delta