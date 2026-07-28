"""Hotel Configuration — Repository 抽象层。

职责：
- 定义 HotelConfigRepository 接口（读写配置）
- 存储实现与业务逻辑分离
- 当前为 YAML 文件存储，后续可切换为数据库
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.hotel_config.models import ReplySettings


@dataclass
class HotelInfo:
    """酒店概要信息。"""

    hotel_id: str
    hotel_name: str


class HotelConfigRepository(ABC):
    """酒店配置仓储接口。"""

    @abstractmethod
    def get_reply_settings(self, hotel_id: str) -> ReplySettings:
        """获取酒店的回复配置。

        Args:
            hotel_id: 酒店 ID

        Returns:
            ReplySettings 实例

        Raises:
            HotelConfigNotFound: 如果配置不存在
        """
        ...

    @abstractmethod
    def update_reply_settings(self, hotel_id: str, settings: ReplySettings) -> None:
        """更新酒店的回复配置。

        Args:
            hotel_id: 酒店 ID
            settings: 新的回复配置
        """
        ...

    @abstractmethod
    def list_hotels(self) -> list[HotelInfo]:
        """列出所有已配置的酒店概要信息。

        Returns:
            HotelInfo 列表（含 hotel_id 和 hotel_name）
        """
        ...

    @abstractmethod
    def create_hotel(self, hotel_id: str, name: str, city: str) -> HotelInfo:
        """创建新的酒店配置。

        生成默认的 seed YAML 文件（metadata/profile/policies/voice）。

        Args:
            hotel_id: 酒店 ID
            name: 酒店名称
            city: 所在城市

        Returns:
            创建的 HotelInfo

        Raises:
            HotelConfigAlreadyExists: 如果酒店已存在
        """
        ...
