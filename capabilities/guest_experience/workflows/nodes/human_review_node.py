"""Human Review Node — Medium 评论人工确认/修改。"""

from langgraph.types import interrupt

from ..state import ReviewReplyState


async def human_review_node(
    state: ReviewReplyState,
) -> ReviewReplyState:
    review_result = interrupt(
        {
            "type": "human_review",
            "reviews_content": state["reviews_content"],
            "reply_content": state["reply_content"],
            "message": "请审核 AI 生成回复",
        }
    )

    return {
        "reply_content": review_result["reply_content"],
    }