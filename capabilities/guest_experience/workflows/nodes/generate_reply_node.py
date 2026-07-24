"""Generate Reply Node — 调用 review_reply_agent 生成回复。"""

from shared.runtime.runtime import run_agent_typed

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult
from capabilities.guest_experience.mappers.reply_input_mapper import ReplyInputMapper

from ..state import ReviewReplyState, WorkflowError


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_result = state.get("anaylay_result")
    if analysis_result is None:
        raise WorkflowError("generate_reply failed: analysis result is None")

    hotel_context = state.get("hotel_context")
    if hotel_context is None:
        raise WorkflowError("generate_reply failed: hotel_context is None")

    input_text = ReplyInputMapper().map(state)
    result = await run_agent_typed("review_reply_agent", input_text, ReplyResult)

    return {"reply_content": result.reply_content}
