"""Low Reply Node — 低严重性评论自动生成回复。"""

import json

from shared.runtime.runtime import run_agent

from ..state import ReviewReplyState


async def low_reply_node(state: ReviewReplyState) -> ReviewReplyState:
    analysis_dict = state.get("anaylay_result")
    if analysis_dict is None:
        reply_content = "感谢您的评论。"
    else:
        # 将分析结果转为字符串作为 agent 输入
        input_text = json.dumps(analysis_dict, ensure_ascii=False)
        result_str = await run_agent("review_reply_agent", input_text)

        # 解析回复内容
        try:
            reply_dict = json.loads(result_str)
            reply_content = reply_dict.get("reply_content", result_str)
        except (json.JSONDecodeError, TypeError):
            reply_content = result_str

    return {"reply_content": reply_content}