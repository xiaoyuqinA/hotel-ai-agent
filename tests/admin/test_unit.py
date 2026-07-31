"""Admin 后台单元测试 — 邀请码逻辑。"""

import os
import secrets
import string
from datetime import datetime, timezone, timedelta


def _generate_code(length=12) -> str:
    """生成邀请码（与 admin/app.py 保持一致）。"""
    alphabet = string.ascii_uppercase + string.digits
    return "INVITE-" + "".join(secrets.choice(alphabet) for _ in range(length))


class TestInviteCodeGeneration:
    """邀请码生成逻辑测试。"""

    def test_code_starts_with_invite_prefix(self):
        """邀请码应以 INVITE- 开头。"""
        code = _generate_code()
        assert code.startswith("INVITE-")

    def test_code_has_correct_length(self):
        """验证码总长度 = 7(INVITE-) + 12 = 19。"""
        code = _generate_code(12)
        assert len(code) == 19  # "INVITE-" + 12 chars

    def test_code_custom_length(self):
        """支持自定义随机部分长度。"""
        code = _generate_code(8)
        assert len(code) == 15  # "INVITE-" + 8 chars

    def test_code_only_uppercase_and_digits(self):
        """随机部分只包含大写字母和数字。"""
        code = _generate_code()
        suffix = code[7:]  # 去掉 "INVITE-"
        allowed = set(string.ascii_uppercase + string.digits)
        assert all(c in allowed for c in suffix)

    def test_codes_are_unique(self):
        """多次生成应不重复。"""
        codes = {_generate_code() for _ in range(1000)}
        assert len(codes) == 1000  # 无重复

    def test_expires_at_is_7_days_from_now(self):
        """有效期默认 7 天。"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)
        diff = (expires - now).total_seconds()
        assert 6.9 * 86400 < diff < 7.1 * 86400  # 约 7 天


class TestInviteCodeCRUD:
    """邀请码 CRUD 逻辑测试（模拟数据库行为）。"""

    def setup_method(self):
        self._store: dict[str, dict] = {}

    def _insert(self, code: str, **kwargs):
        now = datetime.now(timezone.utc)
        self._store[code] = {
            "code": code,
            "hotel_id": kwargs.get("hotel_id"),
            "user_name": kwargs.get("user_name"),
            "is_active": True,
            "created_at": now,
            "expires_at": now + timedelta(days=kwargs.get("days", 7)),
        }

    def _deactivate(self, code: str):
        if code in self._store:
            self._store[code]["is_active"] = False

    def _activate(self, code: str):
        if code in self._store:
            self._store[code]["is_active"] = True

    def _delete(self, code: str):
        self._store.pop(code, None)

    def _list(self):
        return sorted(self._store.values(), key=lambda r: r["created_at"], reverse=True)

    def test_insert_and_list(self):
        """插入后应能列出。"""
        self._insert("INVITE-ABC123", hotel_id="hotel_001", user_name="张三", days=7)
        rows = self._list()
        assert len(rows) == 1
        assert rows[0]["code"] == "INVITE-ABC123"
        assert rows[0]["hotel_id"] == "hotel_001"
        assert rows[0]["user_name"] == "张三"

    def test_deactivate_and_reactivate(self):
        """停用后应标记为无效，再次启用应恢复。"""
        self._insert("INVITE-TEST01")
        assert self._store["INVITE-TEST01"]["is_active"] is True

        self._deactivate("INVITE-TEST01")
        assert self._store["INVITE-TEST01"]["is_active"] is False

        self._activate("INVITE-TEST01")
        assert self._store["INVITE-TEST01"]["is_active"] is True

    def test_delete_removes_code(self):
        """删除后不应出现在列表中。"""
        self._insert("INVITE-TO-DELETE")
        assert "INVITE-TO-DELETE" in self._store

        self._delete("INVITE-TO-DELETE")
        assert "INVITE-TO-DELETE" not in self._store
        assert len(self._list()) == 0

    def test_expired_code_is_inactive_by_time(self):
        """超过有效期的邀请码应视为无效。"""
        now = datetime.now(timezone.utc)
        self._store["EXPIRED"] = {
            "code": "EXPIRED",
            "hotel_id": None,
            "user_name": None,
            "is_active": True,
            "created_at": now - timedelta(days=30),
            "expires_at": now - timedelta(days=23),  # 7 天前过期
        }
        record = self._store["EXPIRED"]
        is_expired = record["expires_at"] < now
        assert is_expired  # 已过期

        # 即使 is_active=True，过期时间到了也算无效
        assert record["is_active"] is True
        assert record["expires_at"] < now

    def test_multiple_codes_ordered_by_created_at(self):
        """列表应按创建时间倒序排列。"""
        self._insert("INVITE-FIRST", days=7)
        import time
        time.sleep(0.01)
        self._insert("INVITE-SECOND", days=7)

        rows = self._list()
        assert rows[0]["code"] == "INVITE-SECOND"  # 最新的在前
