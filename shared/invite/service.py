"""邀请码验证服务 — 与 PostgreSQL 交互，供 api 和 admin 共享。"""

import os
from datetime import datetime, timezone

import asyncpg


POSTGRES_DSN = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'postgres')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'hotel_ai')}"
)


async def get_connection():
    """获取数据库连接。"""
    test_mode = os.getenv("ADMIN_TEST_MODE")
    if test_mode:
        from unittest.mock import AsyncMock
        mock = AsyncMock()
        mock.fetch = AsyncMock(return_value=[])
        mock.execute = AsyncMock(return_value=None)
        return mock
    return await asyncpg.connect(POSTGRES_DSN)


async def save_invite_request(phone: str, name: str) -> str:
    """保存邀请码申请记录（手机号 + 姓名）。

    建表（若不存在）并插入一条申请记录，供客服后续手动发放邀请码。
    手机号已存在时返回 "duplicate" 表示不可重复申请。

    Returns:
        "success": 保存成功
        "duplicate": 该手机号已提交过申请
        "error": 保存失败
    """
    if not phone or not name:
        return "error"
    try:
        conn = await get_connection()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invite_requests (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(32) NOT NULL,
                    name VARCHAR(128) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """
            )
            # 手机号去重校验
            existing = await conn.fetchrow(
                "SELECT id FROM invite_requests WHERE phone = $1",
                phone,
            )
            if existing:
                return "duplicate"
            await conn.execute(
                "INSERT INTO invite_requests (phone, name) VALUES ($1, $2)",
                phone,
                name,
            )
            return "success"
        finally:
            await conn.close()
    except Exception as e:
        logger.error("Save invite request failed: %s", e)
        return "error"


async def validate_invite_code(code: str) -> tuple[bool, str]:
    """验证邀请码有效性。

    Returns:
        (valid: bool, message: str)
    """
    if not code:
        return False, "邀请码不能为空"

    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        try:
            row = await conn.fetchrow(
                "SELECT is_active, expires_at FROM invite_codes WHERE code = $1",
                code,
            )
            if not row:
                return False, "邀请码不存在"
            if not row["is_active"]:
                return False, "邀请码已停用"
            if row["expires_at"] < datetime.now(timezone.utc):
                return False, "邀请码已过期"
            return True, ""
        finally:
            await conn.close()
    except Exception as e:
        logger.error("Invite code validation failed: %s", e)
        return False, "验证服务异常"


try:
    import logging
    logger = logging.getLogger("hotel_ai")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("hotel_ai")
