"""评论处理决策引擎 — 基于规则的业务逻辑，非 LLM。"""

from enum import Enum

from pydantic import BaseModel

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult


class ReviewAction(str, Enum):
    AUTO_REPLY = "auto_reply"
    AI_REPLY_REVIEW = "ai_reply_review"
    HUMAN_REVIEW = "human_review"


class DecisionResult(BaseModel):
    action: ReviewAction
    reason: str


def decide_review_action(analysis_result: ReviewAnalysisResult) -> DecisionResult:
    """根据评论分析结果，决定处理方式。

    规则：
    - High severity → human_review（人工审核）
    - Medium severity → ai_reply_review（AI 回复后人工复核）
    - Low severity → auto_reply（自动回复）
    """
    severity = analysis_result.issue_severity.level

    if severity == "High":
        return DecisionResult(
            action=ReviewAction.HUMAN_REVIEW,
            reason=f"问题严重程度为 {severity}，需要人工优先处理",
        )
    elif severity == "Medium":
        return DecisionResult(
            action=ReviewAction.AI_REPLY_REVIEW,
            reason=f"问题严重程度为 {severity}，由 AI 生成回复后人工复核",
        )
    else:
        return DecisionResult(
            action=ReviewAction.AUTO_REPLY,
            reason=f"问题严重程度为 {severity}，可自动回复",
        )