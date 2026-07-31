"""Langfuse 初始化 — OpenAI Agents SDK 自动追踪入口。"""
import logging
logger = logging.getLogger("hotel_ai")


import config.settings  # 确保 .env 被 load_dotenv 加载
from openinference.instrumentation.openai_agents import (
    OpenAIAgentsInstrumentor
)

from langfuse import get_client


_initialized = False


def init_langfuse():
    global _initialized
    if _initialized:
        return

    # 开启 OpenAI Agents SDK tracing
    OpenAIAgentsInstrumentor().instrument()

    # 初始化 Langfuse client
    langfuse = get_client()

    if langfuse.auth_check():
        logger.info("Langfuse connected")
    else:
        logger.info("Langfuse authentication failed")

    _initialized = True