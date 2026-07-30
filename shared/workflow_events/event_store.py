"""Workflow Event Store — PostgreSQL 持久化 + Redis Pub/Sub。

Phase 2 架构：
- PostgreSQL：事件持久化（Event Sourcing）
- Redis：实时 Pub/Sub（多客户端订阅）

职责：
1. 持久化 WorkflowEvent 到 PostgreSQL
2. 发布事件到 Redis 频道
3. 订阅 Redis 频道获取实时事件
4. 从 PostgreSQL 恢复历史事件（断线恢复）
"""

import asyncio
import json
from typing import Any, AsyncGenerator, AsyncIterator

from datetime import datetime, timezone

import redis.asyncio as redis
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    select,
    and_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from config.settings import get_postgres_url, get_redis_url
from shared.workflow_events.models import (
    WorkflowEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    parse_workflow_event,
)

# ── SQLAlchemy Models ───────────────────────────────────────────────────────────

Base = declarative_base()


class WorkflowRunRecord(Base):
    """workflow_runs 表映射。"""

    __tablename__ = "workflow_runs"

    id = Column(String(64), primary_key=True)
    workflow_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    thread_id = Column(String(128))
    input_data = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    canceled = Column(String(1), default="0")  # "1" = 已取消
    created_at = Column(DateTime(timezone=True), server_default="now()")
    updated_at = Column(
        DateTime(timezone=True), server_default="now()", onupdate="now()"
    )
    completed_at = Column(DateTime(timezone=True))


class WorkflowEventRecord(Base):
    """workflow_events 表映射。"""

    __tablename__ = "workflow_events"

    id = Column(String(64), primary_key=True)
    workflow_id = Column(String(64), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    category = Column(String(32), nullable=False)
    kind = Column(String(64), nullable=False)
    source = Column(String(128))
    payload = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        {"postgresql_partition_by": None},  # 暂时禁用分区，后续可按 workflow_id 分区
    )


# ── Event Store ────────────────────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_engine():
    """获取或创建数据库引擎（延迟初始化）。"""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_postgres_url(),
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    """获取或创建会话工厂。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """初始化数据库表。"""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接。"""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


# ── Event Repository ──────────────────────────────────────────────────────────


async def save_event(event: WorkflowEvent) -> None:
    """持久化单个事件到 PostgreSQL。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        record = WorkflowEventRecord(
            id=event.id,
            workflow_id=event.workflow_id,
            sequence=event.sequence,
            category=event.category,
            kind=event.kind,
            source=event.source,
            payload=event.model_dump(mode="json", exclude_none=True),
        )
        session.add(record)
        await session.commit()


async def get_events_after(
    workflow_id: str,
    last_sequence: int = 0,
) -> list[WorkflowEvent]:
    """获取指定 sequence 之后的历史事件（用于断线恢复）。

    Args:
        workflow_id: 工作流 ID
        last_sequence: 起始序列号（不包含）

    Returns:
        按 sequence 排序的事件列表
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(WorkflowEventRecord)
            .where(
                and_(
                    WorkflowEventRecord.workflow_id == workflow_id,
                    WorkflowEventRecord.sequence > last_sequence,
                )
            )
            .order_by(WorkflowEventRecord.sequence)
        )

        result = await session.execute(stmt)
        records = result.scalars().all()

        events: list[WorkflowEvent] = []
        for r in records:
            payload = dict(r.payload or {})
            # 表字段优先，保证与索引列一致
            payload.update(
                {
                    "id": r.id,
                    "workflow_id": r.workflow_id,
                    "sequence": r.sequence,
                    "category": r.category,
                    "kind": r.kind,
                    "source": r.source,
                }
            )
            events.append(parse_workflow_event(payload))
        return events


# ── Run Repository ─────────────────────────────────────────────────────────────


async def create_run_record(
    run_id: str,
    workflow_name: str,
    thread_id: str,
    input_data: Any = None,
) -> None:
    """创建 workflow_runs 记录。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        record = WorkflowRunRecord(
            id=run_id,
            workflow_name=workflow_name,
            status="pending",
            thread_id=thread_id,
            input_data=input_data,
        )
        session.add(record)
        await session.commit()


async def update_run_status(
    run_id: str,
    status: str,
    result: Any = None,
    error: str = None,
) -> None:
    """更新 workflow_runs 状态。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            update(WorkflowRunRecord)
            .where(WorkflowRunRecord.id == run_id)
            .values(
                status=status,
                result=result,
                error=error,
                updated_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
                if status in ("completed", "failed", "cancelled")
                else None,
            )
        )
        await session.execute(stmt)
        await session.commit()


async def get_run_record(run_id: str) -> dict | None:
    """获取 workflow_runs 记录。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(WorkflowRunRecord).where(WorkflowRunRecord.id == run_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            return {
                "id": record.id,
                "workflow_name": record.workflow_name,
                "status": record.status,
                "thread_id": record.thread_id,
                "result": record.result,
                "error": record.error,
                "canceled": record.canceled == "1",
                "created_at": record.created_at.isoformat()
                if record.created_at
                else None,
            }
        return None


async def cancel_workflow_run(run_id: str) -> bool:
    """标记 workflow_runs 为已取消。

    Args:
        run_id: Workflow Run ID

    Returns:
        是否成功取消
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            update(WorkflowRunRecord)
            .where(WorkflowRunRecord.id == run_id)
            .values(
                canceled="1",
                status="cancelled",
                updated_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.execute(stmt)
        await session.commit()
    return True


async def is_workflow_cancelled(run_id: str) -> bool:
    """检查 workflow 是否已被取消。

    Args:
        run_id: Workflow Run ID

    Returns:
        是否已取消
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(WorkflowRunRecord.canceled).where(WorkflowRunRecord.id == run_id)
        result = await session.execute(stmt)
        canceled = result.scalar_one_or_none()
        return canceled == "1" if canceled is not None else False


# ── Redis Pub/Sub ──────────────────────────────────────────────────────────────

_redis_pool: redis.ConnectionPool | None = None


async def _get_redis() -> redis.Redis:
    """获取 Redis 连接。"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            get_redis_url(),
            decode_responses=True,
        )
    return redis.Redis(connection_pool=_redis_pool)


async def close_redis() -> None:
    """关闭 Redis 连接。"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None


def _channel_name(run_id: str) -> str:
    """生成 Redis 频道名称。"""
    return f"workflow:events:{run_id}"


async def publish_event(event: WorkflowEvent) -> None:
    """发布事件到 Redis 频道。"""
    r = await _get_redis()
    channel = _channel_name(event.workflow_id)
    message = event.model_dump_json()
    await r.publish(channel, message)


async def subscribe_events(run_id: str) -> AsyncGenerator[WorkflowEvent, None]:
    """订阅 Redis 频道获取实时事件。

    收到 __CLOSE__ 信号后自然退出 generator。

    Args:
        run_id: Workflow Run ID

    Yields:
        WorkflowEvent 序列
    """
    r = await _get_redis()
    pubsub = r.pubsub()
    channel = _channel_name(run_id)
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, (str, bytes)):
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    if data == "__CLOSE__":
                        return
                    yield parse_workflow_event(data)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


async def close_channel(run_id: str) -> None:
    """发布关闭信号，让订阅端自然退出。"""
    r = await _get_redis()
    channel = _channel_name(run_id)
    await r.publish(channel, "__CLOSE__")


# ── 组合服务 ──────────────────────────────────────────────────────────────────


async def save_and_publish(event: WorkflowEvent) -> None:
    """持久化 + 发布（原子操作）。"""
    await save_event(event)
    await publish_event(event)


async def subscribe_with_history(
    run_id: str,
    last_sequence: int = 0,
) -> AsyncGenerator[WorkflowEvent, None]:
    """订阅事件流，包含历史事件。

    1. 先发送 last_sequence 之后的历史事件
    2. 检查 run 状态，已完成则不订阅 Redis
    3. 订阅 Redis 实时事件（收到 __CLOSE__ 后自然退出）

    Args:
        run_id: Workflow Run ID
        last_sequence: 起始序列号

    Yields:
        WorkflowEvent 序列
    """
    # 1. 发送历史事件
    historical = await get_events_after(run_id, last_sequence)
    for event in historical:
        yield event

    # 2. 检查 run 是否已完成，已完成则不订阅 Redis
    run = await get_run_record(run_id)
    if run and run["status"] in ("completed", "failed", "cancelled"):
        return

    # 3. 订阅实时事件（收到 __CLOSE__ 后自然退出）
    async for event in subscribe_events(run_id):
        yield event
