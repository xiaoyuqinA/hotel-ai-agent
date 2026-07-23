"""Human Process Node — High 严重性评论人工处理。"""

from langgraph.types import interrupt

from ..state import ReviewReplyState


async def human_process_node(
    state: ReviewReplyState,
) -> ReviewReplyState:
    result = interrupt(
        {
            "type": "human_process",
            "reviews_content": state.get("reviews_content"),
            "analysis_result": state.get("anaylay_result"),
            "message": "该评论风险较高，请人工处理并填写回复内容",
        }
    )

    return {
        "reply_content": result["reply_content"],
    }