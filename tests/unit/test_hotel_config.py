"""Unit tests for Hotel Configuration Service (shared/hotel_config/)."""

import tempfile
from pathlib import Path

import pytest
import yaml

from shared.hotel_config import (
    ReplySettings,
    HotelInfo,
    YamlHotelConfigRepository,
    HotelConfigService,
    HotelConfigNotFound,
)


class TestYamlHotelConfigRepository:
    def test_get_reply_settings(self):
        """读取现有 voice.yaml。"""
        repo = YamlHotelConfigRepository()
        settings = repo.get_reply_settings("hotel_001")

        assert settings.tone == "专业、温暖、真诚"
        assert settings.style == "正式但具有人情味"
        assert len(settings.rules) > 0

    def test_get_reply_settings_not_found(self):
        repo = YamlHotelConfigRepository()
        with pytest.raises(HotelConfigNotFound):
            repo.get_reply_settings("hotel_not_exists")

    def test_list_hotels(self):
        """list_hotels() 返回 HotelInfo 列表，含 hotel_id 和 hotel_name。"""
        repo = YamlHotelConfigRepository()
        hotels = repo.list_hotels()
        assert isinstance(hotels, list)
        assert len(hotels) > 0
        first = hotels[0]
        assert isinstance(first, HotelInfo)
        assert first.hotel_id == "hotel_001"
        assert first.hotel_name == "深圳湾XX酒店"

    def test_list_hotels_with_metadata(self):
        """不存在的 metadata.yaml 时使用目录名作为 hotel_name。"""
        with tempfile.TemporaryDirectory() as tmp:
            hotel_dir = Path(tmp) / "hotel_x"
            hotel_dir.mkdir(parents=True)
            # 只有 voice.yaml，没有 metadata.yaml
            with open(hotel_dir / "voice.yaml", "w") as f:
                yaml.dump({"tone": "x"}, f)

            repo = YamlHotelConfigRepository(base_dir=tmp)
            hotels = repo.list_hotels()
            assert len(hotels) == 1
            assert hotels[0].hotel_id == "hotel_x"
            assert hotels[0].hotel_name == "hotel_x"  # fallback to dir name

    def test_update_reply_settings(self):
        """写入临时目录验证写入逻辑。"""
        with tempfile.TemporaryDirectory() as tmp:
            hotel_dir = Path(tmp) / "hotel_test"
            hotel_dir.mkdir(parents=True)

            voice_path = hotel_dir / "voice.yaml"
            initial = {"tone": "old", "reply_style": "old style", "rules": ["rule1"]}
            with open(voice_path, "w", encoding="utf-8") as f:
                yaml.dump(initial, f, allow_unicode=True)

            repo = YamlHotelConfigRepository(base_dir=tmp)
            settings = repo.get_reply_settings("hotel_test")
            assert settings.tone == "old"

            repo.update_reply_settings("hotel_test", ReplySettings(
                tone="new tone",
                style="new style",
                rules=["new rule"],
            ))

            updated = repo.get_reply_settings("hotel_test")
            assert updated.tone == "new tone"
            assert updated.style == "new style"
            assert updated.rules == ["new rule"]

    def test_update_new_file(self):
        """写入不存在的文件（创建新文件）。"""
        with tempfile.TemporaryDirectory() as tmp:
            repo = YamlHotelConfigRepository(base_dir=tmp)
            repo.update_reply_settings("hotel_new", ReplySettings(
                tone="test tone",
                style="test style",
                rules=["rule a", "rule b"],
            ))

            settings = repo.get_reply_settings("hotel_new")
            assert settings.tone == "test tone"
            assert settings.style == "test style"
            assert settings.rules == ["rule a", "rule b"]


class TestHotelConfigService:
    def test_get_reply_settings(self):
        service = HotelConfigService()
        settings = service.get_reply_settings("hotel_001")
        assert settings.tone == "专业、温暖、真诚"

    def test_update_and_readback(self):
        """通过 Service 写入再读取验证。"""
        with tempfile.TemporaryDirectory() as tmp:
            from shared.hotel_config.yaml_repo import YamlHotelConfigRepository
            repo = YamlHotelConfigRepository(base_dir=tmp)
            service = HotelConfigService(repo=repo)

            service.update_reply_settings("hotel_svc", ReplySettings(
                tone="svc tone",
                style="svc style",
                rules=["svc rule"],
            ))

            settings = service.get_reply_settings("hotel_svc")
            assert settings.tone == "svc tone"

    def test_list_hotels(self):
        service = HotelConfigService()
        hotels = service.list_hotels()
        assert isinstance(hotels, list)
        assert len(hotels) > 0
        assert hotels[0].hotel_id == "hotel_001"
        assert hotels[0].hotel_name == "深圳湾XX酒店"

    def test_not_found(self):
        service = HotelConfigService()
        with pytest.raises(HotelConfigNotFound):
            service.get_reply_settings("not_exists")

    def test_create_hotel(self):
        """创建酒店并验证文件生成。"""
        with tempfile.TemporaryDirectory() as tmp:
            from shared.hotel_config.yaml_repo import YamlHotelConfigRepository
            repo = YamlHotelConfigRepository(base_dir=tmp)
            service = HotelConfigService(repo=repo)

            info = service.create_hotel("hotel_new", "测试酒店", "测试城市")
            assert info.hotel_id == "hotel_new"
            assert info.hotel_name == "测试酒店"

            # 验证 4 个 YAML 文件已生成
            hotel_dir = Path(tmp) / "hotel_new"
            assert (hotel_dir / "metadata.yaml").is_file()
            assert (hotel_dir / "profile.yaml").is_file()
            assert (hotel_dir / "policies.yaml").is_file()
            assert (hotel_dir / "voice.yaml").is_file()

            # 验证配置可读
            settings = service.get_reply_settings("hotel_new")
            assert settings.tone == "专业、温暖、真诚"
            assert settings.style == "正式但具有人情味"

            # 验证列表包含新酒店
            hotels = service.list_hotels()
            ids = [h.hotel_id for h in hotels]
            assert "hotel_new" in ids

    def test_create_hotel_duplicate(self):
        """重复创建应该抛出异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            from shared.hotel_config.yaml_repo import YamlHotelConfigRepository
            from shared.hotel_config.exceptions import HotelConfigAlreadyExists
            repo = YamlHotelConfigRepository(base_dir=tmp)
            service = HotelConfigService(repo=repo)

            service.create_hotel("dup", "测试", "测试")
            with pytest.raises(HotelConfigAlreadyExists):
                service.create_hotel("dup", "测试", "测试")
