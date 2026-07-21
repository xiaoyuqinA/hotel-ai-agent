"""评论处理决策引擎 — 基于规则的业务逻辑，非 LLM。"""

from pydantic import BaseModel
from typing import Literal

class DecisionResult(BaseModel):
    action: Literal["auto_reply", "ai_reply_review", "human_review"]
    reason: str

def decide_review_action(analysis_result) -> DecisionResult:
    """根据评论分析结果，决定处理方式。

    规则：
    - High severity → human_review（人工审核）
    - Medium severity → ai_reply_review（AI 回复后人工复核）
    - Low severity → auto_reply（自动回复）
    """
    severity = analysis_result.issue_severity.level

    if severity == "High":
        return DecisionResult(
            action="human_review",
            reason=f"问题严重程度为 {severity}，需要人工优先处理",
        )
    elif severity == "Medium":
        return DecisionResult(
            action="ai_reply_review",
            reason=f"问题严重程度为 {severity}，由 AI 生成回复后人工复核",
        )
    else:
        return DecisionResult(
            action="auto_reply",
            reason=f"问题严重程度为 {severity}，可自动回复",
        )