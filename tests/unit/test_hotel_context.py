"""Unit tests for HotelContext and HotelContextLoader."""

import pytest
from dataclasses import FrozenInstanceError

from shared.context.hotel_context import (
    HotelProfile,
    HotelPolicies,
    ReplySettings,
    HotelContext,
)
from shared.context.loader import HotelContextLoader
from shared.context.exceptions import HotelContextNotFound


class TestHotelProfile:
    def test_create(self):
        profile = HotelProfile(
            hotel_id="hotel_001",
            name="Test Hotel",
            positioning="Luxury",
            address="123 Main St",
            service_philosophy="Premium service",
        )
        assert profile.hotel_id == "hotel_001"
        assert profile.name == "Test Hotel"
        assert profile.positioning == "Luxury"
        assert profile.address == "123 Main St"
        assert profile.service_philosophy == "Premium service"

    def test_frozen(self):
        profile = HotelProfile(
            hotel_id="hotel_001",
            name="Test Hotel",
            positioning="Luxury",
            address="123 Main St",
            service_philosophy="Premium service",
        )
        with pytest.raises(FrozenInstanceError):
            profile.name = "Changed"


class TestHotelPolicies:
    def test_create(self):
        policies = HotelPolicies(
            breakfast="7:00-10:00",
            parking="Free",
            check_in="14:00",
            check_out="12:00",
        )
        assert policies.breakfast == "7:00-10:00"
        assert policies.parking == "Free"
        assert policies.check_in == "14:00"
        assert policies.check_out == "12:00"

    def test_frozen(self):
        policies = HotelPolicies(
            breakfast="7:00-10:00",
            parking="Free",
            check_in="14:00",
            check_out="12:00",
        )
        with pytest.raises(FrozenInstanceError):
            policies.breakfast = "Changed"


class TestReplySettings:
    def test_create_with_rules(self):
        settings = ReplySettings(
            tone="Professional",
            style="Warm",
            rules=["Rule 1", "Rule 2"],
        )
        assert settings.tone == "Professional"
        assert settings.style == "Warm"
        assert settings.rules == ["Rule 1", "Rule 2"]

    def test_create_without_rules(self):
        settings = ReplySettings(tone="Professional", style="Warm")
        assert settings.rules == []

    def test_mutable(self):
        """ReplySettings 是可变的（可在线修改）。"""
        settings = ReplySettings(tone="Professional", style="Warm")
        settings.tone = "Friendly"
        assert settings.tone == "Friendly"

    def test_serialize(self):
        settings = ReplySettings(
            tone="专业、温暖",
            style="正式",
            rules=["规则1", "规则2"],
        )
        d = {"tone": settings.tone, "style": settings.style, "rules": settings.rules}
        assert d == {
            "tone": "专业、温暖",
            "style": "正式",
            "rules": ["规则1", "规则2"],
        }


class TestHotelContext:
    def test_create(self):
        profile = HotelProfile(
            hotel_id="hotel_001",
            name="Test Hotel",
            positioning="Luxury",
            address="123 Main St",
            service_philosophy="Premium service",
        )
        policies = HotelPolicies(
            breakfast="7:00-10:00",
            parking="Free",
            check_in="14:00",
            check_out="12:00",
        )
        reply_settings = ReplySettings(tone="Professional", style="Warm")
        context = HotelContext(
            hotel_id="hotel_001",
            profile=profile,
            policies=policies,
            reply_settings=reply_settings,
        )
        assert context.hotel_id == "hotel_001"
        assert context.profile == profile
        assert context.policies == policies
        assert context.reply_settings == reply_settings

    def test_frozen(self):
        profile = HotelProfile(
            hotel_id="hotel_001",
            name="Test Hotel",
            positioning="Luxury",
            address="123 Main St",
            service_philosophy="Premium service",
        )
        policies = HotelPolicies(
            breakfast="7:00-10:00",
            parking="Free",
            check_in="14:00",
            check_out="12:00",
        )
        reply_settings = ReplySettings(tone="Professional", style="Warm")
        context = HotelContext(
            hotel_id="hotel_001",
            profile=profile,
            policies=policies,
            reply_settings=reply_settings,
        )
        with pytest.raises(FrozenInstanceError):
            context.hotel_id = "hotel_002"


class TestHotelContextLoader:
    def test_load_hotel_001(self):
        loader = HotelContextLoader()
        context = loader.load("hotel_001")

        assert context.hotel_id == "hotel_001"
        assert context.profile.hotel_id == "hotel_001"
        assert context.profile.name == "深圳湾XX酒店"
        assert context.profile.positioning == "商务精品酒店"
        assert context.profile.address == "深圳市南山区"
        assert context.profile.service_philosophy == "提供专业、温暖、高效的入住体验"
        assert context.policies.breakfast == "7:00-10:00，二楼餐厅提供自助早餐"
        assert context.policies.parking == "地下停车场，住店客人免费"
        assert context.policies.check_in == "14:00"
        assert context.policies.check_out == "12:00"
        assert context.reply_settings.tone == "专业、温暖、真诚"
        assert context.reply_settings.style == "正式但具有人情味"
        assert context.reply_settings.rules == [
            "投诉必须先表达歉意",
            "不推卸责任",
            "避免机械化模板回复",
        ]

    def test_load_nonexistent_hotel(self):
        loader = HotelContextLoader()
        with pytest.raises(HotelContextNotFound) as exc_info:
            loader.load("hotel_999")
        assert exc_info.value.hotel_id == "hotel_999"
