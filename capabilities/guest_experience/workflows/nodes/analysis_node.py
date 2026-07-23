"""Analysis Node — 调用 review_analysis_agent 进行评论分析。"""

from shared.runtime.runtime import run_agent

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult

from ..state import ReviewReplyState


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    reviews_content = state.get("reviews_content", "")

    result = await run_agent("review_analysis_agent", reviews_content)

    # run_agent 返回的可能是 ReviewAnalysisResult 或 JSON 字符串
    if isinstance(result, ReviewAnalysisResult):
        return {"anaylay_result": result}
    if isinstance(result, str):
        try:
            return {"anaylay_result": ReviewAnalysisResult.model_validate_json(result)}
        except Exception:
            pass

    # 兜底
    return {
        "anaylay_result": ReviewAnalysisResult(
            original_comment=reviews_content,
            issue_severity={"level": "Low", "reason": "解析失败，默认低严重性"},
            customer_sentiment={"label": "neutral", "confidence": 0.0},
            customer_intent="mixed",
        )
    }