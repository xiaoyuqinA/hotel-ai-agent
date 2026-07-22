"""Publish Node — 发布内容占位。"""

from ..state import ReviewReplyState


async def publish_node(state: ReviewReplyState) -> ReviewReplyState:
    reply_content = state.get("reply_content", "")
    print(f"[Publish] 发布回复:\n{reply_content}")

    return {"publish_status": "published"}