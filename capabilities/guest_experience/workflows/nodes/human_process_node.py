"""Human Process Node — High 严重性评论人工处理占位。"""

from ..state import ReviewReplyState


async def human_process_node(state: ReviewReplyState) -> ReviewReplyState:
    reviews_content = state.get("reviews_content", "")
    print(f"[Human Process] 高严重性评论需人工处理:\n{reviews_content}")

    return {"publish_status": "handled"}