"""ReplyInputMapper — 构建 Agent 输入 JSON。"""

import json
from dataclasses import asdict

from capabilities.guest_experience.workflows.state import ReviewReplyState


class ReplyInputMapper:
    """构建 review_reply_agent 的输入 JSON。

    使用 model_dump()/asdict() 而非手动字段复制。
    """

    def map(self, state: ReviewReplyState) -> str:
        """将 state 映射为 Agent 输入 JSON。

        Args:
            state: 工作流状态

        Returns:
            JSON 字符串，包含 review、analysis 和 hotel_context
        """
        return json.dumps(
            {
                "original_comment": state["reviews_content"],
                "analysis": state["anaylay_result"].model_dump(),
                "hotel_context": asdict(state["hotel_context"]),
            },
            ensure_ascii=False,
        )
