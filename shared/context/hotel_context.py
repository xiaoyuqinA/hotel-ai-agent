"""HotelContext — 酒店运行上下文。

提供 Review Reply Workflow 生成酒店回复所需的基础信息。
"""

from dataclasses import dataclass

from shared.hotel_config.models import ReplySettings  # noqa: F401


@dataclass(frozen=True)
class HotelProfile:
    """酒店基础档案。"""

    hotel_id: str
    name: str
    positioning: str
    address: str
    service_philosophy: str


@dataclass(frozen=True)
class HotelPolicies:
    """酒店固定政策。"""

    breakfast: str
    parking: str
    check_in: str
    check_out: str


@dataclass(frozen=True)
class HotelContext:
    """酒店运行上下文。

    提供 Review Reply Workflow 生成酒店回复所需的信息。
    """

    hotel_id: str
    profile: HotelProfile
    policies: HotelPolicies
    reply_settings: ReplySettings
