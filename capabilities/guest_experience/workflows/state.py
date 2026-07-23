"""评论运营工作流 State 定义。"""

from typing import TypedDict

from capabilities.guest_experience.agents.review_analysis_agent.schemas import (
    ReviewAnalysisResult,
)


class WorkflowError(Exception):
    """工作流节点执行异常。"""
    pass


class ReviewReplyState(TypedDict):
    reviews_content: str
    anaylay_result: ReviewAnalysisResult | None
    reply_content: str | None
    strategy: str | None
    publish_status: str | None