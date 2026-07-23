"""评论运营工作流 State 定义。"""

from typing import TypedDict

from capabilities.guest_experience.agents.review_analysis_agent.schemas import ReviewAnalysisResult
from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult


class ReviewReplyState(TypedDict, total=False):
    reviews_content: str
    anaylay_result: ReviewAnalysisResult
    reply_content: ReplyResult
    strategy: str
    publish_status: str