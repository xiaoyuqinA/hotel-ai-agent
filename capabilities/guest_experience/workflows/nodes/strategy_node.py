"""Strategy Node — 调用 decide_review_action 判断处理策略并路由。"""

from capabilities.guest_experience.decision.review_decision_engine import (
    ReviewAnalysisResult,
    decide_review_action,
)

from ..state import ReviewReplyState

# 决策引擎枚举 -> 策略字符串映射
STRATEGY_MAP = {
    "auto_reply": "low",
    "ai_reply_review": "medium",
    "human_review": "high",
}


async def strategy_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_dict = state.get("anaylay_result")
    if analysis_dict is None:
        strategy = "low"
    else:
        analysis_result = ReviewAnalysisResult(**analysis_dict)
        decision = decide_review_action(analysis_result)
        strategy = STRATEGY_MAP.get(decision.action, "low")

    return {"strategy": strategy}


def strategy_router(state: ReviewReplyState) -> str:
    """根据 strategy 字段返回路由目标节点名。"""
    strategy = state.get("strategy", "low")
    if strategy == "high":
        return "high"
    elif strategy == "medium":
        return "medium"
    else:
        return "low"