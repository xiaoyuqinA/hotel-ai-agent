"""Generate Reply Node — 流式生成回复，支持 token streaming。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events
from shared.runtime.runtime import run_agent_typed

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from capabilities.guest_experience.mappers.reply_input_mapper import ReplyInputMapper

from ..state import ReviewReplyState, WorkflowError


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    """生成回复 Node — 支持流式 token 输出。

    使用方法：
        1. 发送 NODE_STARTED 事件
        2. 流式消费 Agent token，写入 LangGraph extensions channel
        3. 收集完整回复内容
        4. 发送 NODE_COMPLETED 事件

    通过 get_stream_writer() 写入的事件会被 ProjectionMapper 消费，
    最终通过 WebSocket 推送给 Chrome Extension。
    """
    writer = get_stream_writer()

    # 发送 NODE_STARTED
    writer({
        "type": "node_started",
        "node": "generate_reply",
        "display_name": "生成回复",
    })

    try:
        analysis_result = state.get("anaylay_result")
        if analysis_result is None:
            raise WorkflowError("generate_reply failed: analysis result is None")

        hotel_context = state.get("hotel_context")
        if hotel_context is None:
            raise WorkflowError("generate_reply failed: hotel_context is None")

        input_text = ReplyInputMapper().map(state)

        # 流式消费 Agent 输出
        reply_content = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_reply_agent", input_text
        ):
            if event_type == "token":
                writer({
                    "type": "token",
                    "delta": chunk,
                    "source": "generate_reply",
                })
                reply_content += chunk
            elif event_type == "node_error":
                writer({
                    "type": "node_error",
                    "node": "generate_reply",
                    "error": chunk,
                })

        # NODE_COMPLETED
        writer({
            "type": "node_completed",
            "node": "generate_reply",
        })

        return {"reply_content": reply_content}

    except Exception as e:
        writer({
            "type": "node_error",
            "node": "generate_reply",
            "error": str(e),
        })
        raise
