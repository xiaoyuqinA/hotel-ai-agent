"""Hotel Configuration Service — 酒店配置业务入口。

职责：
1. 查询/更新回复配置（ReplySettings）
2. 通过 Repository 抽象隔离存储实现
3. 供 HotelContextLoader 和 API 端点使用
"""

from shared.hotel_config.models import ReplySettings
from shared.hotel_config.repository import HotelConfigRepository, HotelInfo
from shared.hotel_config.yaml_repo import YamlHotelConfigRepository


class HotelConfigService:
    """酒店配置服务。

    提供 ReplySettings 的读写操作。
    默认使用 YamlHotelConfigRepository（YAML 文件存储）。
    """

    def __init__(self, repo: HotelConfigRepository | None = None):
        self._repo = repo or YamlHotelConfigRepository()

    def get_reply_settings(self, hotel_id: str) -> ReplySettings:
        """获取酒店的回复配置。

        Args:
            hotel_id: 酒店 ID

        Returns:
            ReplySettings 实例

        Raises:
            HotelConfigNotFound: 如果配置不存在
        """
        return self._repo.get_reply_settings(hotel_id)

    def update_reply_settings(self, hotel_id: str, settings: ReplySettings) -> None:
        """更新酒店的回复配置。

        Args:
            hotel_id: 酒店 ID
            settings: 新的回复配置
        """
        self._repo.update_reply_settings(hotel_id, settings)

    def list_hotels(self) -> list[HotelInfo]:
        """列出所有已配置的酒店概要信息。"""
        return self._repo.list_hotels()

    def create_hotel(self, hotel_id: str, name: str, city: str) -> HotelInfo:
        """创建新的酒店配置。

        Args:
            hotel_id: 酒店 ID
            name: 酒店名称
            city: 所在城市

        Returns:
            创建的 HotelInfo
        """
        return self._repo.create_hotel(hotel_id, name, city)
