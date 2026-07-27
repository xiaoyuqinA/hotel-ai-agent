"""Workflow Event Publisher — WebSocket / SSE 事件推送。"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from shared.workflow_events.models import WorkflowEvent


router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowEventPublisher:
    """工作流事件发布器接口。

    抽象层，支持：
    - WebSocket（连接管理）
    - SSE（HTTP 长连接）
    - 内存队列（测试用）
    """

    async def publish(self, event: WorkflowEvent) -> None:
        """发布单个事件。"""
        raise NotImplementedError

    async def publish_stream(
        self, events: AsyncGenerator[WorkflowEvent, None]
    ) -> AsyncGenerator[str, None]:
        """将事件流转换为 SSE 格式。"""
        async for event in events:
            await self.publish(event)
            yield format_sse_event(event)


def format_sse_event(event: WorkflowEvent) -> str:
    """将 WorkflowEvent 格式化为 SSE 格式。

    SSE 格式：data: {"kind": "...", ...}\n\n
    """
    data = event.model_dump_json()
    return f"data: {data}\n\n"


async def sse_workflow_endpoint(
    request: Request,
    workflow_name: str,
) -> Response:
    """SSE 端点 — 运行工作流并通过 SSE 推送事件。

    使用方式：
        GET /workflow/{workflow_name}/stream?input=xxx&thread_id=xxx

    返回 SSE 流，每个事件格式：
        data: {"kind": "workflow_started", "workflow_id": "...", ...}\n\n
    """
    # 从 request 获取参数
    body = await request.json()
    user_input = body.get("input")
    thread_id = body.get("thread_id")

    # 运行工作流
    from shared.workflow_events.streaming_runner import stream_workflow

    events = stream_workflow(workflow_name, user_input, thread_id)

    async def event_generator():
        async for event in events:
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx buffering
        },
    )


# 注册路由
router.add_api_route(
    "/{workflow_name}/stream",
    sse_workflow_endpoint,
    methods=["POST"],
    response_class=Response,
    summary="流式运行工作流",
    description="通过 Server-Sent Events 流式推送工作流事件",
)
