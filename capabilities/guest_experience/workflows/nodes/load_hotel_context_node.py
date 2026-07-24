"""Load Hotel Context Node — 加载酒店上下文到 state。"""

from shared.context.loader import HotelContextLoader

from ..state import ReviewReplyState


async def load_hotel_context_node(state: ReviewReplyState) -> ReviewReplyState:
    """加载酒店上下文。

    作为 workflow 的第一个节点（entry point），在 analysis 之前执行。
    从 state 中的 hotel_id 加载 HotelContext 并放入 state。
    """
    hotel_id = state.get("hotel_id") or "hotel_001"
    loader = HotelContextLoader()
    hotel_context = loader.load(hotel_id)
    return {"hotel_context": hotel_context}
