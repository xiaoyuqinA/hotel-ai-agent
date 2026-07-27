"""统一配置加载入口 — 整个项目唯一调用 load_dotenv 的地方。"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE", "chat_completions")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Application
ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Langfuse
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "")

# ── PostgreSQL（Phase 2: Workflow Event Store）───────────────────────────────
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "hotel_ai")


def get_postgres_url() -> str:
    """构建 PostgreSQL 连接 URL。"""
    return (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


# ── Redis（Phase 2: Real-time Pub/Sub）────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))


def get_redis_url() -> str:
    """构建 Redis 连接 URL。"""
    return f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"