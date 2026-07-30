"""Strategy Node — 调用 decide_review_action 判断处理策略并路由。"""

from capabilities.guest_experience.decision.review_decision_engine import (
    decide_review_action,
)

from ..state import ReviewReplyState, WorkflowError


async def strategy_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_result = state.get("anaylay_result")
    if analysis_result is None:
        raise WorkflowError("strategy failed: analysis result is None")

    decision = decide_review_action(analysis_result)
    return {"strategy": decision.action.value}


def strategy_router(state: ReviewReplyState) -> str:
    """返回策略字符串，作为路由目标。"""
    return state.get("strategy", "auto_reply")


def reply_router(state: ReviewReplyState) -> str:
    """生成回复后，根据策略路由：auto_reply → publish，ai_reply_review → human_review。"""
    return state.get("strategy", "auto_reply")
