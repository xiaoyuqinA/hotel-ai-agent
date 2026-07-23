"""Human Review Node — Medium 评论人工审核占位。"""

from ..state import ReviewReplyState


async def human_review_node(state: ReviewReplyState) -> ReviewReplyState:
    reply_content = state.get("reply_content")
    if reply_content is not None:
        print(f"[Human Review] 请审核以下 AI 生成的回复:\n{reply_content}")

    return {"publish_status": "reviewed"}