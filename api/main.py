"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as agent_router
from api.sse import router as sse_router
from shared.runtime.workflow_runtime import WorkflowRuntime

# ── Global Runtime ──────────────────────────────────────────────────────────────

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
        print(f"Warning: Event Store not available (PostgreSQL/Redis): {e}")
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
app.state.runtime = _runtime
