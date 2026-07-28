"""Hotel Configuration API — Chrome Extension 配置管理端点。

GET    /api/hotels                             → 列出所有已配置酒店
POST   /api/hotels                             → 创建新酒店
GET    /api/hotels/{hotel_id}/reply-settings   → 查询回复配置
PUT    /api/hotels/{hotel_id}/reply-settings   → 更新回复配置
"""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.hotel_config import (
    HotelConfigService,
    HotelInfo,
    ReplySettings,
)
from shared.hotel_config.exceptions import HotelConfigNotFound, HotelConfigAlreadyExists

router = APIRouter(prefix="/api/hotels", tags=["hotel-config"])

# Service 单例（延迟初始化）
_config_service: HotelConfigService | None = None


def _get_service() -> HotelConfigService:
    global _config_service
    if _config_service is None:
        _config_service = HotelConfigService()
    return _config_service


class ReplySettingsPayload(ReplySettings):
    """API 请求/响应 Schema。"""

    pass


def _to_payload(settings: ReplySettings) -> ReplySettingsPayload:
    return ReplySettingsPayload(
        tone=settings.tone,
        style=settings.style,
        rules=settings.rules,
    )


class CreateHotelRequest(BaseModel):
    """创建酒店请求体。"""

    name: str
    city: str


def _generate_hotel_id(name: str) -> str:
    """从酒店名称生成 hotel_id。
    仅使用小写字母、数字、下划线，保证 URL 安全。
    示例：'深圳湾万豪酒店' → 'hotel_a1b2c3d4'
    """
    import hashlib

    # 用名称的 MD5 前 8 位作为短 hash，保证唯一
    short_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"hotel_{short_hash}"


@router.get("", summary="列出所有已配置酒店")
async def list_hotels() -> list[HotelInfo]:
    """返回所有已配置 reply-settings 的酒店概要。"""
    return _get_service().list_hotels()


@router.post("", summary="创建新酒店", status_code=201)
async def create_hotel(body: CreateHotelRequest) -> HotelInfo:
    """创建新酒店配置，生成默认的 seed YAML 文件。"""
    hotel_id = _generate_hotel_id(body.name)
    try:
        return _get_service().create_hotel(hotel_id, body.name, body.city)
    except HotelConfigAlreadyExists:
        # 如果 ID 冲突，加时间戳后缀
        import time

        hotel_id = f"{hotel_id}_{int(time.time())}"
        return _get_service().create_hotel(hotel_id, body.name, body.city)


@router.get(
    "/{hotel_id}/reply-settings",
    summary="获取酒店回复配置",
    response_model=ReplySettingsPayload,
)
async def get_reply_settings(hotel_id: str):
    """获取指定酒店的回复配置（ReplySettings）。"""
    try:
        settings = _get_service().get_reply_settings(hotel_id)
        return _to_payload(settings)
    except HotelConfigNotFound:
        raise HTTPException(
            status_code=404, detail=f"Hotel config not found: {hotel_id}"
        )


@router.put(
    "/{hotel_id}/reply-settings",
    summary="更新酒店回复配置",
)
async def update_reply_settings(hotel_id: str, body: ReplySettingsPayload):
    """更新指定酒店的回复配置。"""
    try:
        settings = ReplySettings(
            tone=body.tone,
            style=body.style,
            rules=body.rules,
        )
        _get_service().update_reply_settings(hotel_id, settings)
        return {"status": "ok", "hotel_id": hotel_id}
    except HotelConfigNotFound:
        raise HTTPException(
            status_code=404, detail=f"Hotel config not found: {hotel_id}"
        )
