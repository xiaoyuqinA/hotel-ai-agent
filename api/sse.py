"""评论运营 SSE 端点 — 通过 Server-Sent Events 流式推送工作流事件。"""

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from shared.workflow_events.models import WorkflowEvent
from shared.streaming.runner import WorkflowRunner

router = APIRouter(prefix="/review", tags=["review"])


def format_sse_event(event: WorkflowEvent) -> str:
    """将 WorkflowEvent 格式化为 SSE 格式。"""
    return f"data: {event.model_dump_json()}\n\n"


async def review_operation_stream(request: Request) -> Response:
    """评论运营流式端点。

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
    summary="评论运营流式处理",
    description="通过 SSE 流式推送 AI 分析和生成回复的事件",
)
