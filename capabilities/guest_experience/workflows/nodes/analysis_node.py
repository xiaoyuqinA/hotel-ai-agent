"""Analysis Node — 调用 review_analysis_agent 进行评论分析。"""

import json

from shared.runtime.runtime import run_agent

from ..state import ReviewReplyState


async def analysis_node(state: ReviewReplyState) -> ReviewReplyState:
    reviews_content = state.get("reviews_content", "")

    result_str = await run_agent("review_analysis_agent", reviews_content)

    # 解析 LLM 返回的 JSON 结果为 dict
    try:
        analysis_dict = json.loads(result_str)
    except (json.JSONDecodeError, TypeError):
        # 如果无法解析，返回带原始信息的兜底 dict
        analysis_dict = {
            "original_comment": reviews_content,
            "issue_severity": {"level": "Low", "reason": "解析失败，默认低严重性"},
            "customer_sentiment": {"label": "neutral", "confidence": 0.0},
            "customer_intent": "mixed",
        }

    return {"anaylay_result": analysis_dict}