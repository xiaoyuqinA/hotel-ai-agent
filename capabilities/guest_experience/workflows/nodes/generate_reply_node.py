"""Generate Reply Node — 生成回复，发送业务事件。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events
from shared.workflow_events.kinds import BusinessEvent

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from capabilities.guest_experience.mappers.reply_input_mapper import ReplyInputMapper

from ..state import ReviewReplyState, WorkflowError


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    """生成回复 Node。

    业务事件：
    - generation_started: 开始生成回复
    - generation_completed: 生成完成
    - generation_failed: 生成失败

    Token 流式输出由 LangGraph messages projection 自动处理。
    """
    writer = get_stream_writer()

    writer({
        "event": BusinessEvent.GENERATION_STARTED,
        "message": "正在生成回复",
    })

    try:
        analysis_result = state.get("anaylay_result")
        if analysis_result is None:
            raise WorkflowError("generate_reply failed: analysis result is None")

        hotel_context = state.get("hotel_context")
        if hotel_context is None:
            raise WorkflowError("generate_reply failed: hotel_context is None")

        input_text = ReplyInputMapper().map(state)

        # 流式消费 Agent 输出（token 由 messages projection 处理）
        reply_content = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_reply_agent", input_text
        ):
            if event_type == "token":
                reply_content += chunk
            elif event_type == "node_error":
                writer({
                    "event": BusinessEvent.GENERATION_FAILED,
                    "error": chunk,
                })

        writer({
            "event": BusinessEvent.GENERATION_COMPLETED,
            "result": {"reply_content": reply_content},
        })

        return {"reply_content": reply_content}

    except Exception as e:
        writer({
            "event": BusinessEvent.GENERATION_FAILED,
            "error": str(e),
        })
        raise
