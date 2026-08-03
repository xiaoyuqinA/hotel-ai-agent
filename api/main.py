"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as agent_router
from api.sse import router as sse_router
from api.hotel_config import router as hotel_config_router
from shared.runtime.workflow_runtime import WorkflowRuntime

# ── 日志配置 ──────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
)

# 覆写 Uvicorn 的 access log 格式
for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uvicorn_logger = logging.getLogger(name)
    for handler in uvicorn_logger.handlers:
        handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

logger = logging.getLogger("hotel_ai")

# ── Global Runtime ─────────────────────────────────────────────────────────────

_runtime = WorkflowRuntime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    Phase 2/3 启动顺序：
    1. WorkflowRuntime（LangGraph checkpointer）
    2. PostgreSQL（Event Store + Human Approval）
    3. Redis（Pub/Sub）
    """
    # Startup
    await _runtime.startup()

    # Phase 2: 初始化 Event Store
    try:
        from shared.workflow_events.event_store import init_db, close_db, close_redis
        await init_db()
        app.state.event_store_initialized = True
    except Exception as e:
        logger.warning("Event Store not available (PostgreSQL/Redis): %s", e)
        app.state.event_store_initialized = False

    yield

    # Shutdown
    await _runtime.shutdown()

    # Phase 2: 清理 Event Store
    if app.state.event_store_initialized:
        from shared.workflow_events.event_store import close_db, close_redis
        await close_redis()
        await close_db()


app = FastAPI(
    title="Hotel AI Agents API",
    lifespan=lifespan,
)

app.include_router(agent_router)
app.include_router(sse_router)
app.include_router(hotel_config_router)
app.state.runtime = _runtime

# 静态文件（隐私政策等）
from pathlib import Path
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
