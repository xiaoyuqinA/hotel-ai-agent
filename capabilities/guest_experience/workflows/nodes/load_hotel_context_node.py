"""Load Hotel Context Node — 加载酒店上下文到 state。"""

from shared.context.hotel_context import (
    HotelContext,
    HotelPolicies,
    HotelProfile,
    ReplySettings,
)
from shared.context.loader import HotelContextLoader

from ..state import ReviewReplyState


def _from_frontend(data: dict) -> HotelContext:
    """将前端传来的 hotel_context dict 转为 HotelContext 对象。"""
    rs = data.get("reply_settings", {})
    return HotelContext(
        hotel_id=data.get("hotel_id", ""),
        profile=HotelProfile(
            hotel_id=data.get("hotel_id", ""),
            name=data.get("name", ""),
            positioning="",
            address="",
            service_philosophy="",
        ),
        policies=HotelPolicies(
            breakfast="",
            parking="",
            check_in="",
            check_out="",
        ),
        reply_settings=ReplySettings(
            tone=rs.get("tone", ""),
            style=rs.get("style", ""),
            rules=rs.get("rules", []),
        ),
    )


async def load_hotel_context_node(state: ReviewReplyState) -> ReviewReplyState:
    """加载酒店上下文。

    作为 workflow 的第一个节点（entry point），在 analysis 之前执行。
    优先级：
      1. state 中已有 hotel_context（前端传来）→ 直接转换使用
      2. 有 hotel_id → 从 YAML 加载
      3. 无任何信息 → hotel_context 为 None，使用默认配置
    """
    # 前端传来的 hotel_context（dict）优先
    frontend_ctx = state.get("hotel_context")
    if frontend_ctx and isinstance(frontend_ctx, dict):
        return {"hotel_context": _from_frontend(frontend_ctx)}

    # YAML 加载
    hotel_id = state.get("hotel_id")
    if hotel_id:
        loader = HotelContextLoader()
        hotel_context = loader.load(hotel_id)
        return {"hotel_context": hotel_context}

    return {"hotel_context": None}
