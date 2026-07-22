"""评论运营工作流 State 定义。"""

from typing import TypedDict, Optional


class ReviewReplyState(TypedDict, total=False):
    reviews_content: str
    anaylay_result: Optional[dict]
    reply_content: Optional[str]
    strategy: Optional[str]
    publish_status: Optional[str]