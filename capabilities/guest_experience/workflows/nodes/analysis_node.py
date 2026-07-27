"""Analysis Node — 流式分析评论，支持 token streaming。"""

from langgraph.config import get_stream_writer

from shared.runtime.streaming import stream_agent_with_events

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState, WorkflowError


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    """分析评论 Node — 支持流式 token 输出。

    使用方法：
        1. 发送 NODE_STARTED 事件
        2. 流式消费 Agent token，写入 LangGraph extensions channel
        3. 收集完整输出并解析为 ReviewAnalysisResult
        4. 发送 NODE_COMPLETED 事件
    """
    writer = get_stream_writer()

    # 发送 NODE_STARTED
    writer({
        "type": "node_started",
        "node": "analysis",
        "display_name": "AI分析评论",
    })

    try:
        reviews_content = state.get("reviews_content", "")

        # 流式消费 Agent 输出
        accumulated = ""
        async for event_type, chunk in stream_agent_with_events(
            "review_analysis_agent", reviews_content
        ):
            if event_type == "token":
                writer({
                    "type": "token",
                    "delta": chunk,
                    "source": "analysis",
                })
                accumulated += chunk
            elif event_type == "node_error":
                writer({
                    "type": "node_error",
                    "node": "analysis",
                    "error": chunk,
                })

        # 解析最终结果
        result = ReviewAnalysisResult.model_validate_json(accumulated)

        # NODE_COMPLETED
        writer({
            "type": "node_completed",
            "node": "analysis",
        })

        return {"anaylay_result": result}

    except Exception as e:
        writer({
            "type": "node_error",
            "node": "analysis",
            "error": str(e),
        })
        raise
