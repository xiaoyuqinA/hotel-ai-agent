"""YAML 实现的 HotelConfigRepository。

从 resources/hotels/{hotel_id}/voice.yaml 读写回复配置。
作为初始 seed 数据源，后续可替换为 DB 实现。
"""

import os
from pathlib import Path

import yaml

from shared.hotel_config.exceptions import HotelConfigNotFound, HotelConfigAlreadyExists
from shared.hotel_config.models import ReplySettings
from shared.hotel_config.repository import HotelConfigRepository, HotelInfo


class YamlHotelConfigRepository(HotelConfigRepository):
    """YAML 文件实现的配置仓储。

    读写 resources/hotels/{hotel_id}/voice.yaml。
    """

    def __init__(self, base_dir: str | Path = ""):
        self._base = Path(base_dir) if base_dir else self._default_base()

    @staticmethod
    def _default_base() -> Path:
        """默认：项目根目录下的 resources/hotels。"""
        return Path(__file__).resolve().parents[2] / "resources" / "hotels"

    def _resolve_path(self, hotel_id: str) -> Path:
        return self._base / hotel_id / "voice.yaml"

    def get_reply_settings(self, hotel_id: str) -> ReplySettings:
        path = self._resolve_path(hotel_id)
        if not path.is_file():
            raise HotelConfigNotFound(hotel_id)
        data = self._load_yaml(path)
        return ReplySettings(
            tone=data.get("tone", ""),
            # voice.yaml 使用 reply_style 作为 key，ReplySettings 用 style
            style=data.get("reply_style", data.get("style", "")),
            rules=data.get("rules", []),
        )

    def update_reply_settings(self, hotel_id: str, settings: ReplySettings) -> None:
        path = self._resolve_path(hotel_id)
        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        # 保留原有数据，只覆盖相关字段
        # 写回 voice.yaml 时使用 reply_style（YAML 原始 key）
        data = {
            "tone": settings.tone,
            "reply_style": settings.style,
            "rules": settings.rules,
        }
        if path.is_file():
            existing = self._load_yaml(path)
            existing.update(data)
            data = existing

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def list_hotels(self) -> list[HotelInfo]:
        if not self._base.is_dir():
            return []
        result = []
        for d in sorted(self._base.iterdir()):
            if not d.is_dir() or not (d / "voice.yaml").is_file():
                continue
            hotel_name = d.name  # fallback
            meta_path = d / "metadata.yaml"
            if meta_path.is_file():
                meta = self._load_yaml(meta_path)
                hotel_name = meta.get("hotel_name", d.name)
            result.append(HotelInfo(hotel_id=d.name, hotel_name=hotel_name))
        return result

    def create_hotel(self, hotel_id: str, name: str, city: str) -> HotelInfo:
        """创建新酒店配置，生成 4 个 seed YAML 文件。"""
        hotel_dir = self._base / hotel_id
        if hotel_dir.is_dir():
            raise HotelConfigAlreadyExists(hotel_id)

        hotel_dir.mkdir(parents=True)

        # metadata.yaml
        metadata = {"hotel_id": hotel_id, "hotel_name": name}
        with open(hotel_dir / "metadata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

        # profile.yaml
        profile = {
            "hotel_id": hotel_id,
            "name": name,
            "positioning": f"{city}精品酒店",
            "address": f"{city}",
            "service_philosophy": "提供专业、温暖、高效的入住体验",
        }
        with open(hotel_dir / "profile.yaml", "w", encoding="utf-8") as f:
            yaml.dump(profile, f, allow_unicode=True, default_flow_style=False)

        # policies.yaml
        policies = {
            "breakfast": "7:00-10:00，餐厅提供自助早餐",
            "parking": "住店客人免费停车",
            "check_in": "14:00",
            "check_out": "12:00",
        }
        with open(hotel_dir / "policies.yaml", "w", encoding="utf-8") as f:
            yaml.dump(policies, f, allow_unicode=True, default_flow_style=False)

        # voice.yaml
        voice = {
            "tone": "专业、温暖、真诚",
            "reply_style": "正式但具有人情味",
            "rules": [
                "投诉必须先表达歉意",
                "不推卸责任",
                "避免机械化模板回复",
            ],
        }
        with open(hotel_dir / "voice.yaml", "w", encoding="utf-8") as f:
            yaml.dump(voice, f, allow_unicode=True, default_flow_style=False)

        return HotelInfo(hotel_id=hotel_id, hotel_name=name)

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
