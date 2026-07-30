"""Generate Reply Node — 生成回复，发送业务事件。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from capabilities.guest_experience.mappers.reply_input_mapper import ReplyInputMapper

from ..state import ReviewReplyState, WorkflowError
from shared.workflow_events.emitter import NodeEventEmitter


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    """生成回复 Node。

    业务事件：
    - generation_started: 开始生成回复
    - generation_completed: 生成完成
    - generation_failed: 生成失败

    Token 流式输出由 LangGraph messages projection 自动处理。
    """
    writer = get_stream_writer()
    emitter = NodeEventEmitter(writer)

    emitter.generation_started()

    try:
        analysis_result = state.get("anaylay_result")
        if analysis_result is None:
            raise WorkflowError("generate_reply failed: analysis result is None")

        hotel_context = state.get("hotel_context")
        # hotel_context 可选：无 hotel_id 时为 None，Agent 使用默认配置

        input_text = ReplyInputMapper.map(state)
        print(f"[GenerateReply] hotel_context present: {hotel_context is not None}")
        print(f"[GenerateReply] Agent input JSON (first 500 chars):\n{input_text[:500]}")

        reply_content = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_reply_agent", input_text
        ):
            if event_type == "token":
                reply_content += chunk
                emitter.token_delta(chunk)
            elif event_type == "node_error":
                emitter.generation_failed(chunk)

        emitter.generation_completed(reply_content=reply_content)

        return {"reply_content": reply_content}

    except Exception as e:
        emitter.generation_failed(str(e))
        raise
