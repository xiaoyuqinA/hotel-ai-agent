"""Model factory for creating agent models from environment configuration."""

from openai import AsyncOpenAI

from agents.models.openai_chatcompletions import (
    OpenAIChatCompletionsModel,
)
from agents.models.openai_responses import (
    OpenAIResponsesModel,
)
from config.settings import LLM_PROVIDER, OPENAI_API_TYPE, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_API_KEY


def create_agent_model():
    """Create an agent model based on LLM_PROVIDER and OPENAI_API_TYPE.

    Business agents should only call this function.
    Switching between Chat Completions / Responses API requires only
    changing ``OPENAI_API_TYPE`` in .env, zero code modification.
    """
    provider = LLM_PROVIDER
    api_type = OPENAI_API_TYPE

    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )

    if provider == "openai":
        if api_type == "chat_completions":
            return OpenAIChatCompletionsModel(
                model=OPENAI_MODEL,
                openai_client=client,
            )
        elif api_type == "responses":
            return OpenAIResponsesModel(
                model=OPENAI_MODEL,
                openai_client=client,
            )

        raise ValueError(
            f"Unsupported OPENAI_API_TYPE: {api_type}. "
            "Expected 'responses' or 'chat_completions'."
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")