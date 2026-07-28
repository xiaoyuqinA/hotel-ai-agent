"""评论运营 SSE 端点 — Phase 3: PostgreSQL + Redis Event Store。

POST /review/run
→ 创建 run + 后台任务 + 返回 run_id

GET /review/stream/{run_id}
→ 订阅 run 的事件队列（支持断线恢复）
"""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, StreamingResponse

from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowCancelledEvent,
)
from shared.workflow_events.event_store import (
    create_run_record,
    get_run_record,
    save_and_publish,
    subscribe_with_history,
    cancel_workflow_run,
)
from shared.streaming.runner import WorkflowRunner

router = APIRouter(prefix="/review", tags=["review"])


def format_sse_event(event: WorkflowEvent) -> str:
    """将 WorkflowEvent 格式化为 SSE 格式。"""
    return f"data: {event.model_dump_json()}\n\n"


async def _run_workflow_background(
    run_id: str,
    workflow_name: str,
    input_data: dict,
    config: dict,
    runtime,
) -> None:
    """后台任务：运行 LangGraph 并发布事件到 PostgreSQL + Redis。"""
    from shared.workflow_events.event_store import update_run_status

    try:
        workflow = runtime.get_workflow(workflow_name)

        await update_run_status(run_id, "running")

        started_event = WorkflowStartedEvent.create(run_id)
        await save_and_publish(started_event)

        runner = WorkflowRunner(workflow_id=run_id)

        result = None
        terminal_published = False
        async for event in runner.run(workflow.graph, input_data, config):
            await save_and_publish(event)
            if event.kind in ("workflow_completed", "workflow_failed"):
                terminal_published = True
                result = event.payload.get("result")

        if not terminal_published and runner.is_cancelled:
            await save_and_publish(WorkflowCancelledEvent.create(run_id))
            await update_run_status(run_id, "cancelled")
        else:
            await update_run_status(run_id, "completed", result=result)

    except Exception as e:
        await save_and_publish(WorkflowFailedEvent.create(run_id, str(e)))
        try:
            await update_run_status(run_id, "failed", error=str(e))
        except Exception:
            pass


async def create_review_run(request: Request) -> dict:
    """创建 Workflow Run。

    POST /review/run
    Content-Type: application/json
    {"reviews_content": "...", "thread_id": "xxx", "hotel_id": "hotel_001"}

    返回：
    {"run_id": "run_xxx", "status": "pending"}
    """
    body = await request.json()
    reviews_content = body.get("reviews_content", "")
    thread_id = body.get("thread_id", "")
    hotel_id = body.get("hotel_id", "")

    runtime = request.app.state.runtime
    workflow = runtime.get_workflow("review_operation")

    # 生成 run_id 和 thread_id
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    thread_id = thread_id or f"thread_{uuid.uuid4().hex[:12]}"

    # 创建 run 记录
    await create_run_record(
        run_id=run_id,
        workflow_name="review_operation",
        thread_id=thread_id,
        input_data=reviews_content,
    )

    # 准备 input 和 config
    # 如果前端传了 hotel_id，以 tuple (hotel_id, reviews_content) 形式传入
    # input_mapper 会解析出 hotel_id
    if hotel_id:
        input_data = workflow.input_mapper((hotel_id, reviews_content))
    else:
        input_data = workflow.input_mapper(reviews_content)
    config = {"configurable": {"thread_id": thread_id}}

    # 启动后台任务
    asyncio.create_task(
        _run_workflow_background(
            run_id,
            "review_operation",
            input_data,
            config,
            runtime,
        )
    )

    return {
        "run_id": run_id,
        "status": "pending",
        "thread_id": thread_id,
    }


router.add_api_route(
    "/run",
    create_review_run,
    methods=["POST"],
    summary="创建评论运营 Workflow Run",
    description="创建 Workflow Run，返回 run_id 用于后续 SSE 订阅",
)


async def stream_review_run(request: Request, run_id: str) -> Response:
    """订阅 Workflow Run 的事件流（SSE）。

    GET /review/stream/{run_id}

    支持断线恢复：如果事件已经产生，会先发送历史事件，再继续监听新事件。

    查询参数：
        last_sequence: 从指定 sequence 之后开始（用于断线恢复）
    """
    # 检查 run 是否存在
    run = await get_run_record(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # 获取 last_sequence（用于断线恢复）
    last_sequence = int(request.query_params.get("last_sequence", 0))

    async def event_generator():
        # 订阅事件流（包含历史事件 + 实时事件）
        async for event in subscribe_with_history(run_id, last_sequence):
            yield format_sse_event(event)

            # workflow_completed / workflow_failed / workflow_cancelled 后退出
            if event.kind in (
                "workflow_completed",
                "workflow_failed",
                "workflow_cancelled",
            ):
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
    run = await get_run_record(run_id)

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


async def _do_cancel_workflow_run(run_id: str) -> dict:
    """取消 Workflow Run。

    POST /review/run/{run_id}/cancel

    返回：
    {"success": true, "run_id": "...", "message": "Workflow cancelled"}
    """
    run = await get_run_record(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if run.get("status") in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel workflow with status: {run.get('status')}",
        )

    await cancel_workflow_run(run_id)

    return {
        "success": True,
        "run_id": run_id,
        "message": "Workflow cancelled",
    }


router.add_api_route(
    "/run/{run_id}/cancel",
    _do_cancel_workflow_run,
    methods=["POST"],
    summary="取消 Workflow Run",
    description="取消正在运行的 Workflow Run",
)
