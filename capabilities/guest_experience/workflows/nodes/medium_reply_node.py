"""Medium Reply Node — 中等严重性评论自动生成回复（需后续人工审核）。"""

import json

from shared.runtime.runtime import run_agent

from ..state import ReviewReplyState


async def medium_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_dict = state.get("anaylay_result")
    if analysis_dict is None:
        reply_content = "感谢您的评论，我们会认真处理。"
    else:
        input_text = json.dumps(analysis_dict, ensure_ascii=False)
        result_str = await run_agent("review_reply_agent", input_text)

        try:
            reply_dict = json.loads(result_str)
            reply_content = reply_dict.get("reply_content", result_str)
        except (json.JSONDecodeError, TypeError):
            reply_content = result_str

    return {"reply_content": reply_content}