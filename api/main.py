"""FastAPI application entry point."""

from fastapi import FastAPI

from api.routes import router as agent_router
from api.sse import router as sse_router
from shared.runtime.workflow_runtime import WorkflowRuntime

app = FastAPI(title="Hotel AI Agents API")

# 全局 runtime 实例
_runtime = WorkflowRuntime()


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 workflow runtime。"""
    await _runtime.startup()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理 runtime。"""
    await _runtime.shutdown()


app.include_router(agent_router)
app.include_router(sse_router)
app.state.runtime = _runtime
