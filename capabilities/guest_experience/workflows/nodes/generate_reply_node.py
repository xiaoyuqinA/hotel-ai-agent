"""Generate Reply Node — 调用 review_reply_agent 生成回复。"""

import json

from shared.runtime.runtime import run_agent

from capabilities.guest_experience.agents.review_reply_agent.schemas import ReplyResult

from ..state import ReviewReplyState


async def generate_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_result = state.get("anaylay_result")
    if analysis_result is None:
        return {"reply_content": "感谢您的评论。"}

    input_text = json.dumps(analysis_result.model_dump(), ensure_ascii=False)
    result = await run_agent("review_reply_agent", input_text)

    # 提取 str 回复内容
    if isinstance(result, ReplyResult):
        return {"reply_content": result.reply_content}
    if isinstance(result, str):
        try:
            reply = ReplyResult.model_validate_json(result)
            return {"reply_content": reply.reply_content}
        except Exception:
            return {"reply_content": result}

    return {"reply_content": "感谢您的评论。"}