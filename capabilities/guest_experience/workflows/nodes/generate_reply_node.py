"""Generate Reply Node — 流式生成回复，支持 token streaming。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events
from shared.runtime.runtime import run_agent_typed
from shared.workflow_events.kinds import BusinessEvent

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from capabilities.guest_experience.mappers.reply_input_mapper import ReplyInputMapper

from ..state import ReviewReplyState, WorkflowError


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    """生成回复 Node — 支持流式 token 输出。

    业务事件：
    - generation_started: 开始生成回复
    - generation_completed: 生成完成
    - generation_failed: 生成失败

    Token 事件通过 messages 投影消费。
    通过 get_stream_writer() 写入的事件被 ProjectionMapper 消费。
    """
    writer = get_stream_writer()

    # 发送业务开始事件
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

        # 流式消费 Agent 输出
        reply_content = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_reply_agent", input_text
        ):
            if event_type == "token":
                # token 事件通过 messages 投影自动处理
                writer({
                    "type": "token",
                    "delta": chunk,
                    "source": "generation",
                })
                reply_content += chunk
            elif event_type == "node_error":
                writer({
                    "event": BusinessEvent.GENERATION_FAILED,
                    "error": chunk,
                })

        # 发送业务完成事件
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
