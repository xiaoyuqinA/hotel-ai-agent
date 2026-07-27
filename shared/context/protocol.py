"""HotelContextProvider Protocol — 抽象酒店上下文加载接口。

未来可切换到数据库或 RAG 配置时，只需实现新 provider，
Workflow 无需修改。
"""

from typing import Protocol, runtime_checkable

from shared.context.hotel_context import HotelContext


@runtime_checkable
class HotelContextProvider(Protocol):
    """酒店上下文提供者接口。"""

    def load(self, hotel_id: str) -> HotelContext:
        """加载指定酒店的上下文。

        Args:
            hotel_id: 酒店 ID

        Returns:
            HotelContext 实例
        """
        ...
