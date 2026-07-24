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
    # 人工任务类型，用于区分 High 分支不同场景
    human_task_type: str | None
    publish_status: str | None
    # 工作流会话 ID，用于 interrupt 后恢复
    thread_id: str | None