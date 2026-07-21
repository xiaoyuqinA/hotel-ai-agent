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