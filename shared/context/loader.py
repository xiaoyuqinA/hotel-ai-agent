"""HotelContextLoader — 从 YAML 配置文件加载 HotelContext。"""

from pathlib import Path

from shared.context.exceptions import HotelContextNotFound
from shared.context.hotel_context import (
    HotelContext,
    HotelPolicies,
    HotelProfile,
    ReplySettings,
)
from shared.context.parser.yaml_parser import YamlParser
from shared.context.protocol import HotelContextProvider
from shared.hotel_config.exceptions import HotelConfigNotFound
from shared.hotel_config.service import HotelConfigService

RESOURCES_DIR = Path(__file__).resolve().parents[2] / "resources"


class HotelContextLoader(HotelContextProvider):
    """从 YAML 配置文件加载 HotelContext。

    经过三阶段演进：
    Phase 1: 直接读 YAML 文件（初始）
    Phase 2: 通过 HotelConfigService 获取 ReplySettings（当前）
    Phase 3: 全部通过 Repository 抽象（未来）
    """

    def __init__(
        self,
        resources_dir: Path | None = None,
        config_service: HotelConfigService | None = None,
    ):
        self._resources_dir = resources_dir or RESOURCES_DIR
        self._config_service = config_service or HotelConfigService()
        self._parser = YamlParser()

    def load(self, hotel_id: str) -> HotelContext:
        """加载指定酒店的上下文。

        Args:
            hotel_id: 酒店 ID

        Returns:
            HotelContext 实例

        Raises:
            HotelContextNotFound: 如果酒店目录不存在
        """
        hotel_dir = self._resources_dir / "hotels" / hotel_id
        if not hotel_dir.is_dir():
            raise HotelContextNotFound(hotel_id)

        metadata = self._load_metadata(hotel_dir)
        profile = self._load_profile(hotel_dir, metadata)
        policies = self._load_policies(hotel_dir)

        # 通过 HotelConfigService 获取 ReplySettings（可在线修改）
        try:
            reply_settings = self._config_service.get_reply_settings(hotel_id)
        except HotelConfigNotFound:
            raise HotelContextNotFound(hotel_id)

        return HotelContext(
            hotel_id=hotel_id,
            profile=profile,
            policies=policies,
            reply_settings=reply_settings,
        )

    def _load_metadata(self, hotel_dir: Path) -> dict:
        metadata_path = hotel_dir / "metadata.yaml"
        return self._parser.parse(metadata_path)

    def _load_profile(self, hotel_dir: Path, metadata: dict) -> HotelProfile:
        profile_path = hotel_dir / "profile.yaml"
        data = self._parser.parse(profile_path)

        return HotelProfile(
            hotel_id=metadata["hotel_id"],
            name=metadata["hotel_name"],
            positioning=data["positioning"],
            address=data["address"],
            service_philosophy=data["service_philosophy"],
        )

    def _load_policies(self, hotel_dir: Path) -> HotelPolicies:
        policies_path = hotel_dir / "policies.yaml"
        data = self._parser.parse(policies_path)

        return HotelPolicies(
            breakfast=data["breakfast"],
            parking=data["parking"],
            check_in=data["check_in"],
            check_out=data["check_out"],
        )
