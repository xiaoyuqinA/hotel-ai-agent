"""Human Approval Service — Phase 3: 人工审批服务。

功能：
1. 记录 interrupt 状态
2. 提供审批 API
3. 触发 workflow resume

架构：
┌─────────────────┐
│  LangGraph      │
│  interrupt()    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  ApprovalStore  │
│  (PostgreSQL)  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Chrome Ext     │
│  /admin panel   │
└─────────────────┘
        │
        ▼
POST /approval/{approval_id}/resolve
        │
        ▼
workflow.resume()
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, String, Text, DateTime, JSON, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.workflow_events.event_store import (
    _get_session_factory,
    _get_engine,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ApprovalStatus(str, Enum):
    """审批状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRecord(Base):
    """approvals 表映射。"""

    __tablename__ = "workflow_approvals"

    id = Column(String(64), primary_key=True)
    run_id = Column(String(64), nullable=False, index=True)
    thread_id = Column(String(128), nullable=False)
    workflow_name = Column(String(128), nullable=False)
    task_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False, default={})
    status = Column(String(32), nullable=False, default="pending")
    resolution = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default="now()")
    resolved_at = Column(DateTime(timezone=True))


# ── Approval Service ───────────────────────────────────────────────────────────

async def create_approval(
    run_id: str,
    thread_id: str,
    workflow_name: str,
    task_type: str,
    payload: dict[str, Any],
) -> dict:
    """创建人工审批记录。

    Args:
        run_id: WorkflowRun ID
        thread_id: LangGraph thread ID（用于 resume）
        workflow_name: workflow 名称
        task_type: interrupt 类型（human_review / human_process）
        payload: interrupt 携带的数据

    Returns:
        Approval 记录
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        record = ApprovalRecord(
            id=f"approval_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            thread_id=thread_id,
            workflow_name=workflow_name,
            task_type=task_type,
            payload=payload,
            status=ApprovalStatus.PENDING.value,
        )
        session.add(record)
        await session.commit()

        return {
            "id": record.id,
            "run_id": record.run_id,
            "thread_id": record.thread_id,
            "workflow_name": record.workflow_name,
            "task_type": record.task_type,
            "payload": record.payload,
            "status": record.status,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


async def get_approval(approval_id: str) -> dict | None:
    """获取审批记录。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(ApprovalRecord).where(ApprovalRecord.id == approval_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            return {
                "id": record.id,
                "run_id": record.run_id,
                "thread_id": record.thread_id,
                "workflow_name": record.workflow_name,
                "task_type": record.task_type,
                "payload": record.payload,
                "status": record.status,
                "resolution": record.resolution,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
            }
        return None


async def list_pending_approvals() -> list[dict]:
    """列出所有待审批记录。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(ApprovalRecord)
            .where(ApprovalRecord.status == ApprovalStatus.PENDING.value)
            .order_by(ApprovalRecord.created_at.desc())
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "thread_id": r.thread_id,
                "workflow_name": r.workflow_name,
                "task_type": r.task_type,
                "payload": r.payload,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]


async def resolve_approval(
    approval_id: str,
    action: str,  # "approve" | "reject"
    resolution: dict[str, Any],
) -> dict | None:
    """审批决策。

    Args:
        approval_id: 审批 ID
        action: "approve" | "reject"
        resolution: 审批结果（如修改后的 reply_content）

    Returns:
        更新后的审批记录，None 如果不存在
    """
    from shared.runtime.workflow_runtime import _runtime

    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(ApprovalRecord).where(ApprovalRecord.id == approval_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return None

        if action == "approve":
            record.status = ApprovalStatus.APPROVED.value
            record.resolution = resolution
        else:
            record.status = ApprovalStatus.REJECTED.value
            record.resolution = resolution

        # 触发 workflow resume
        runtime = _runtime()
        await runtime.resume(
            workflow_name=record.workflow_name,
            thread_id=record.thread_id,
            data=resolution,
        )

        await session.commit()

        return {
            "id": record.id,
            "status": record.status,
            "resolution": record.resolution,
        }


async def get_approvals_by_run(run_id: str) -> list[dict]:
    """获取指定 run 的所有审批记录。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(ApprovalRecord)
            .where(ApprovalRecord.run_id == run_id)
            .order_by(ApprovalRecord.created_at)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "id": r.id,
                "task_type": r.task_type,
                "status": r.status,
                "payload": r.payload,
                "resolution": r.resolution,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
