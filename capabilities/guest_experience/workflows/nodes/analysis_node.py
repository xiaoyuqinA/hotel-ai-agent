"""Analysis Node — 流式分析评论，支持 token streaming。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events
from shared.workflow_events.kinds import BusinessEvent

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState, WorkflowError


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    """分析评论 Node — 支持流式 token 输出。

    业务事件：
    - analysis_started: 开始分析
    - analysis_completed: 分析完成
    - analysis_failed: 分析失败

    Token 事件通过 messages 投影消费。
    """
    writer = get_stream_writer()

    # 发送业务开始事件
    writer({
        "event": BusinessEvent.ANALYSIS_STARTED,
        "message": "正在分析客户评论",
    })

    try:
        reviews_content = state.get("reviews_content", "")

        # 流式消费 Agent 输出
        accumulated = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_analysis_agent", reviews_content
        ):
            if event_type == "token":
                # token 事件通过 messages 投影自动处理
                writer({
                    "type": "token",
                    "delta": chunk,
                    "source": "analysis",
                })
                accumulated += chunk
            elif event_type == "node_error":
                writer({
                    "event": BusinessEvent.ANALYSIS_FAILED,
                    "error": chunk,
                })

        # 解析最终结果
        result = ReviewAnalysisResult.model_validate_json(accumulated)

        # 发送业务完成事件
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
