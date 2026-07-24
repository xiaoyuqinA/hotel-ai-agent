"""Generate Reply Node — 调用 review_reply_agent 生成回复。"""

import json

from shared.runtime.runtime import run_agent

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult

from ..state import ReviewReplyState, WorkflowError


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_result = state.get("anaylay_result")
    if analysis_result is None:
        raise WorkflowError("generate_reply failed: analysis result is None")

    input_text = json.dumps({
        "original_comment": state["reviews_content"],
        "analysis": analysis_result.model_dump(),
    }, ensure_ascii=False)
    result = await run_agent("review_reply_agent", input_text)

    if isinstance(result, ReplyResult):
        return {"reply_content": result.reply_content}
    if isinstance(result, str):
        try:
            reply = ReplyResult.model_validate_json(result)
            return {"reply_content": reply.reply_content}
        except Exception:
            return {"reply_content": result}

    raise WorkflowError("generate_reply failed: unable to parse result")