"""ReplyInputMapper — 构建 Agent 输入 JSON。"""
import logging
logger = logging.getLogger("hotel_ai")


import json
from dataclasses import asdict, dataclass

from capabilities.guest_experience.workflows.state import ReviewReplyState


def _to_dict(obj):
    """将任意对象转为 dict，兼容 dataclass / dict / None。"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dataclass_fields__"):
        return {f: _to_dict(getattr(obj, f)) for f in obj.__dataclass_fields__}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


class ReplyInputMapper:
    """构建 review_reply_agent 的输入 JSON。"""

    @staticmethod
    def map(state: ReviewReplyState) -> str:
        """将 state 映射为 Agent 输入 JSON。"""
        analysis = state["anaylay_result"]
        analysis_data = _to_dict(analysis)

        hotel_context = state.get("hotel_context")
        ctx = _to_dict(hotel_context) if hotel_context else None

        result = {
            "original_comment": state["reviews_content"],
            "analysis": analysis_data,
            "hotel_context": ctx,
            # 回复语言（zh / en），prompt 据此决定输出语言
            "language": state.get("language", "zh") or "zh",
        }
        logger.info("Full Agent input JSON:\n%s", json.dumps(result, ensure_ascii=False, default=str))
        return json.dumps(result, ensure_ascii=False, default=str)
