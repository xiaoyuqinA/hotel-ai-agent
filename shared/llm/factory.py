"""Model factory for creating agent models from environment configuration."""

import os

from openai import AsyncOpenAI

from agents.models.openai_chatcompletions import (
    OpenAIChatCompletionsModel,
)
from agents.models.openai_responses import (
    OpenAIResponsesModel,
)


def create_agent_model():
    """Create an agent model based on LLM_PROVIDER and OPENAI_API_TYPE.

    Business agents should only call this function.
    Switching between Chat Completions / Responses API requires only
    changing ``OPENAI_API_TYPE`` in .env, zero code modification.
    """
    provider = os.getenv("LLM_PROVIDER", "openai")
    api_type = os.getenv("OPENAI_API_TYPE", "responses")

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )

    if provider == "openai":
        if api_type == "chat_completions":
            return OpenAIChatCompletionsModel(
                model=os.environ["OPENAI_MODEL"],
                openai_client=client,
            )
        elif api_type == "responses":
            return OpenAIResponsesModel(
                model=os.environ["OPENAI_MODEL"],
                openai_client=client,
            )

        raise ValueError(
            f"Unsupported OPENAI_API_TYPE: {api_type}. "
            "Expected 'responses' or 'chat_completions'."
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")