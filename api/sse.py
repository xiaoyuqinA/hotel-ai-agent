"""评论运营 SSE 端点 — 通过 Server-Sent Events 流式推送工作流事件。"""

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from shared.workflow_events.models import WorkflowEvent

router = APIRouter(prefix="/review", tags=["review"])


def format_sse_event(event: WorkflowEvent) -> str:
    """将 WorkflowEvent 格式化为 SSE 格式。"""
    return f"data: {event.model_dump_json()}\n\n"


async def review_operation_stream(request: Request) -> Response:
    """评论运营流式端点。

    POST /review/operation/stream
    Content-Type: application/json
    {"reviews_content": "...", "thread_id": "xxx"}

    返回 SSE 流：
        data: {"kind": "workflow_started", ...}\n\n
        data: {"kind": "node_started", "payload": {"node": "analysis"}}\n\n
        data: {"kind": "token_delta", "payload": {"delta": "正在"}}\n\n
        data: {"kind": "workflow_completed", ...}\n\n
    """
    body = await request.json()
    reviews_content = body.get("reviews_content", "")
    thread_id = body.get("thread_id", "")

    from shared.workflow_events.streaming_runner import stream_workflow

    async def event_generator():
        async for event in stream_workflow(
            "review_operation",
            reviews_content,
            thread_id,
        ):
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
    summary="评论运营流式处理",
    description="通过 SSE 流式推送 AI 分析和生成回复的事件",
)
