"""评论运营 SSE 端点 — 支持同步和异步两种模式。

模式 1（同步，已实现）：
    POST /review/stream
    → LangGraph → SSE 流

模式 2（异步，支持 Phase 1 和 Phase 2）：
    POST /review/run
    → 创建 run + 后台任务 + 返回 run_id

    GET /review/stream/{run_id}
    → 订阅 run 的事件队列（支持断线恢复）

Phase 1: 内存 asyncio.Queue
Phase 2: PostgreSQL + Redis Pub/Sub
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, StreamingResponse

from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
)
from shared.workflow_events.run_manager import (
    get_run_manager as get_memory_manager,
    RunStatus as MemoryRunStatus,
)
from shared.streaming.runner import WorkflowRunner

router = APIRouter(prefix="/review", tags=["review"])


def format_sse_event(event: WorkflowEvent) -> str:
    """将 WorkflowEvent 格式化为 SSE 格式。"""
    return f"data: {event.model_dump_json()}\n\n"


# ════════════════════════════════════════════════════════════════════════════════
# 模式 1：同步 SSE（现有逻辑）
# ════════════════════════════════════════════════════════════════════════════════


async def review_operation_stream(request: Request) -> Response:
    """评论运营流式端点（同步模式）。

    POST /review/stream
    Content-Type: application/json
    {"reviews_content": "...", "thread_id": "xxx"}

    返回 SSE 流：
        data: {"category": "system", "kind": "workflow_started", ...}\n\n
        data: {"category": "progress", "kind": "node_started", ...}\n\n
        data: {"category": "message", "kind": "token_delta", ...}\n\n
        data: {"category": "system", "kind": "workflow_completed", ...}\n\n
    """
    body = await request.json()
    reviews_content = body.get("reviews_content", "")
    thread_id = body.get("thread_id", "")

    runtime = request.app.state.runtime
    workflow = runtime.get_workflow("review_operation")

    async def event_generator():
        runner = WorkflowRunner()
        input_data = workflow.input_mapper(reviews_content)
        config = {"configurable": {"thread_id": thread_id}}

        async for event in runner.run(workflow.graph, input_data, config):
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


router.add_api_route(
    "/stream",
    review_operation_stream,
    methods=["POST"],
    summary="评论运营流式处理（同步模式）",
    description="通过 SSE 流式推送 AI 分析和生成回复的事件",
)


# ════════════════════════════════════════════════════════════════════════════════
# 模式 2：异步 SSE（Phase 1 / Phase 2）
# ════════════════════════════════════════════════════════════════════════════════


def _get_manager(request: Request):
    """根据配置获取对应的 manager。

    Phase 2 优先使用 Redis manager。
    """
    if getattr(request.app.state, "event_store_initialized", False):
        from shared.workflow_events.redis_run_manager import get_run_manager
        return get_run_manager()
    else:
        return get_memory_manager()


def _get_status(request: Request):
    """根据配置获取对应的 RunStatus。"""
    if getattr(request.app.state, "event_store_initialized", False):
        from shared.workflow_events.redis_run_manager import RunStatus
        return RunStatus
    else:
        return MemoryRunStatus


# ── Phase 1: 内存 Queue 后台任务 ──────────────────────────────────────────────


async def _run_workflow_memory(
    run_id: str,
    workflow_name: str,
    input_data: dict,
    config: dict,
) -> None:
    """Phase 1 后台任务：使用内存 Queue。"""
    from shared.runtime.workflow_runtime import _runtime

    manager = get_memory_manager()
    Status = MemoryRunStatus

    try:
        await manager.set_status(run_id, Status.RUNNING)

        # 发布 workflow_started
        await manager.publish_event(run_id, WorkflowStartedEvent.create(run_id))

        # 获取 workflow graph
        runtime = _runtime()
        workflow = runtime.get_workflow(workflow_name)

        # 运行 workflow
        runner = WorkflowRunner(workflow_id=run_id)

        result = None
        async for event in runner.run(workflow.graph, input_data, config):
            await manager.publish_event(run_id, event)
            if event.kind == "workflow_completed":
                result = event.payload.get("result")

        await manager.set_result(run_id, result)

    except Exception as e:
        await manager.publish_event(run_id, WorkflowFailedEvent.create(run_id, str(e)))
        await manager.set_error(run_id, str(e))

    finally:
        run = await manager.get_run(run_id)
        if run:
            status = Status.FAILED if run.error else Status.COMPLETED
            await manager.set_status(run_id, status)


# ── Phase 2: Redis 后台任务 ───────────────────────────────────────────────────


async def _run_workflow_redis(
    run_id: str,
    workflow_name: str,
    input_data: dict,
    config: dict,
) -> None:
    """Phase 2 后台任务：使用 PostgreSQL + Redis。"""
    from shared.workflow_events.redis_run_manager import run_workflow_background
    await run_workflow_background(run_id, workflow_name, input_data, config)


# ── API 端点 ───────────────────────────────────────────────────────────────────


async def create_review_run(request: Request) -> dict:
    """创建 Workflow Run（异步模式）。

    POST /review/run
    Content-Type: application/json
    {"reviews_content": "...", "thread_id": "xxx"}

    返回：
    {"run_id": "run_xxx", "status": "pending"}
    """
    body = await request.json()
    reviews_content = body.get("reviews_content", "")
    thread_id = body.get("thread_id", "")

    runtime = request.app.state.runtime
    workflow = runtime.get_workflow("review_operation")

    # 根据配置选择 manager
    manager = _get_manager(request)
    run = await manager.create_run(
        workflow_name="review_operation",
        input_data=reviews_content,
        thread_id=thread_id,
    )

    # 准备 input 和 config
    input_data = workflow.input_mapper(reviews_content)
    config = {"configurable": {"thread_id": run["thread_id"]}}

    # 根据配置选择后台任务
    if getattr(request.app.state, "event_store_initialized", False):
        task = _run_workflow_redis(
            run["id"],
            "review_operation",
            input_data,
            config,
        )
    else:
        task = _run_workflow_memory(
            run["id"],
            "review_operation",
            input_data,
            config,
        )

    asyncio.create_task(task)

    return {
        "run_id": run["id"],
        "status": run["status"],
        "thread_id": run["thread_id"],
    }


router.add_api_route(
    "/run",
    create_review_run,
    methods=["POST"],
    summary="创建评论运营 Workflow Run（异步模式）",
    description="创建 Workflow Run，返回 run_id 用于后续 SSE 订阅",
)


async def stream_review_run(request: Request, run_id: str) -> Response:
    """订阅 Workflow Run 的事件流（SSE）。

    GET /review/stream/{run_id}

    支持断线恢复：如果事件已经产生，会先发送历史事件，再继续监听新事件。

    查询参数：
        last_sequence: 从指定 sequence 之后开始（用于断线恢复）
    """
    manager = _get_manager(request)

    # 检查 run 是否存在
    run = await manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # 获取 last_sequence（用于断线恢复）
    last_sequence = int(request.query_params.get("last_sequence", 0))

    async def event_generator():
        # 先发送 run 状态
        yield format_sse_event(WorkflowStartedEvent.create(run_id))

        # 订阅事件流
        async for event in manager.subscribe(run_id, last_sequence):
            if event.sequence > last_sequence:
                yield format_sse_event(event)

            # workflow_completed 后退出
            if event.kind == "workflow_completed":
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


router.add_api_route(
    "/stream/{run_id}",
    stream_review_run,
    methods=["GET"],
    summary="订阅 Workflow Run 事件流",
    description="通过 SSE 订阅指定 run 的事件流，支持断线恢复",
)


async def get_run_status(request: Request, run_id: str) -> dict:
    """获取 Workflow Run 状态。

    GET /review/run/{run_id}

    返回：
    {"run_id": "...", "status": "running", "result": {...}}
    """
    manager = _get_manager(request)
    run = await manager.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return {
        "run_id": run["id"],
        "workflow_name": run["workflow_name"],
        "status": run["status"],
        "thread_id": run["thread_id"],
        "result": run.get("result"),
        "error": run.get("error"),
    }


router.add_api_route(
    "/run/{run_id}",
    get_run_status,
    methods=["GET"],
    summary="获取 Workflow Run 状态",
    description="查询 Workflow Run 的当前状态和结果",
)
