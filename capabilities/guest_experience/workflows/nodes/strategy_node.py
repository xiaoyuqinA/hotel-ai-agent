"""Strategy Node — 调用 decide_review_action 判断处理策略并路由。"""

from capabilities.guest_experience.decision.review_decision_engine import (
    ReviewAction,
    decide_review_action,
)

from ..state import ReviewReplyState


async def strategy_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_result = state.get("anaylay_result")
    if analysis_result is None:
        # 分析失败无法判断风险，默认走人工处理
        strategy = "high"
    else:
        decision = decide_review_action(analysis_result)
        if decision.action == ReviewAction.HUMAN_REVIEW:
            strategy = "high"
        elif decision.action == ReviewAction.AI_REPLY_REVIEW:
            strategy = "medium"
        else:
            strategy = "low"

    return {"strategy": strategy}


def strategy_router(state: ReviewReplyState) -> str:
    """返回策略字符串，作为路由目标。"""
    return state.get("strategy", "high")


def reply_router(state: ReviewReplyState) -> str:
    """生成回复后，根据策略路由：low → publish，medium → human_review。"""
    return state.get("strategy", "low")