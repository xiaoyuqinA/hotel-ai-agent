"""评论运营 SSE 端点 — Phase 3: PostgreSQL + Redis Event Store。

POST /review/run
→ 创建 run + 后台任务 + 返回 run_id

GET /review/stream/{run_id}
→ 订阅 run 的事件队列（支持断线恢复）
"""

import asyncio
import json as _json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, StreamingResponse

logger = logging.getLogger("hotel_ai")

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
    close_channel,
)
from shared.streaming.runner import WorkflowRunner
from shared.workflow_events.display_names import DisplayName

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

        started_event = WorkflowStartedEvent.create(
            run_id,
            display_name=DisplayName.WORKFLOW_STARTED,
        )
        started_event.sequence = 0
        await save_and_publish(started_event)

        runner = WorkflowRunner(workflow_id=run_id)

        result = None
        async for event in runner.run(workflow.graph, input_data, config):
            await save_and_publish(event)
            if isinstance(event, WorkflowCompletedEvent):
                result = event.result
            elif isinstance(event, WorkflowFailedEvent):
                result = {"error": event.error}

        if runner.is_cancelled:
            await save_and_publish(
                WorkflowCancelledEvent.create(
                    run_id, display_name=DisplayName.WORKFLOW_CANCELLED
                )
            )
            await update_run_status(run_id, "cancelled")
        else:
            await update_run_status(run_id, "completed", result=result)

    except Exception as e:
        logger.error("Workflow run failed: %s", str(e))
        try:
            await save_and_publish(
                WorkflowFailedEvent.create(
                    run_id, str(e), display_name=DisplayName.WORKFLOW_FAILED
                )
            )
        except Exception as e2:
            logger.error("Failed to publish failure event: %s", str(e2))
        try:
            await update_run_status(run_id, "failed", error=str(e))
        except Exception as e3:
            logger.error("Failed to update run status: %s", str(e3))
    finally:
        await close_channel(run_id)


async def create_review_run(request: Request) -> dict:
    """创建 Workflow Run。

    POST /review/run
    Content-Type: application/json
    {"reviews_content": "...", "thread_id": "xxx", "hotel_context": {...}}

    返回：
    {"run_id": "run_xxx", "status": "pending"}
    """
    body = await request.json()
    reviews_content = body.get("reviews_content", "")
    thread_id = body.get("thread_id", "")
    hotel_context = body.get("hotel_context")

    import json as _json
    logger.info("POST /review/run request: %s", _json.dumps(body, ensure_ascii=False, default=str))

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
    # 如果前端传了 hotel_context，直接注入 state，跳过 YAML 加载
    if hotel_context:
        input_data = workflow.input_mapper((hotel_context, reviews_content))
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

    response_data = {
        "run_id": run_id,
        "status": "pending",
        "thread_id": thread_id,
    }
    logger.info("POST /review/run response: %s", _json.dumps(response_data, ensure_ascii=False, default=str))
    return response_data


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
        HEARTBEAT_INTERVAL = 15

        # Chrome EventSource 在收到最后一个 data: 后约 2 秒会触发 onerror。
        # 必须在订阅事件流之前立即发一个注释行，重置计时器。
        yield ": connected\n\n"

        event_iter = subscribe_with_history(run_id, last_sequence)

        while True:
            try:
                event = await asyncio.wait_for(
                    event_iter.__anext__(),
                    timeout=HEARTBEAT_INTERVAL,
                )
                yield format_sse_event(event)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
            except StopAsyncIteration:
                return

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
