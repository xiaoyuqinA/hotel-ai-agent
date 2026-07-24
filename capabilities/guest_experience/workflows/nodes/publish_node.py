"""Publish Node — 发布内容占位。"""

from langgraph.config import get_config

from ..state import ReviewReplyState


async def publish_node(state: ReviewReplyState) -> ReviewReplyState:
    reply_content = state.get("reply_content")
    if reply_content is not None:
        print(f"[Publish] 发布回复:\n{reply_content}")

    config = get_config()
    thread_id = config.get("configurable", {}).get("thread_id")

    return {"publish_status": "published", "thread_id": thread_id}