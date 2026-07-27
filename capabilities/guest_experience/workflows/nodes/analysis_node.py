"""Analysis Node — 分析评论，发送业务事件。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events
from shared.workflow_events.kinds import BusinessEvent

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    """分析评论 Node。

    业务事件：
    - analysis_started: 开始分析
    - analysis_completed: 分析完成
    - analysis_failed: 分析失败

    Token 流式输出由 LangGraph messages projection 自动处理。
    """
    writer = get_stream_writer()

    writer({
        "event": BusinessEvent.ANALYSIS_STARTED,
        "message": "正在分析客户评论",
    })

    try:
        reviews_content = state.get("reviews_content", "")

        # 流式消费 Agent 输出（token 由 messages projection 处理）
        accumulated = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_analysis_agent", reviews_content
        ):
            if event_type == "token":
                accumulated += chunk
            elif event_type == "node_error":
                writer({
                    "event": BusinessEvent.ANALYSIS_FAILED,
                    "error": chunk,
                })

        result = ReviewAnalysisResult.model_validate_json(accumulated)

        writer({
            "event": BusinessEvent.ANALYSIS_COMPLETED,
            "result": result.model_dump(),
        })

        return {"anaylay_result": result}

    except Exception as e:
        writer({
            "event": BusinessEvent.ANALYSIS_FAILED,
            "error": str(e),
        })
        raise
