"""Workflow History Service — Phase 3: 历史记录查询。

功能：
1. 分页查询历史 run
2. 查询指定 run 的完整事件流
3. Event Replay 支持
4. 统计信息
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func, and_, desc

from shared.workflow_events.event_store import (
    _get_session_factory,
    WorkflowRunRecord,
    WorkflowEventRecord,
)


async def list_runs(
    workflow_name: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """分页查询历史 run。

    Args:
        workflow_name: 可选，按 workflow 名称过滤
        status: 可选，按状态过滤
        limit: 每页数量
        offset: 偏移量

    Returns:
        {
            "runs": [...],
            "total": 100,
            "limit": 20,
            "offset": 0,
        }
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        # 构建查询
        conditions = []
        if workflow_name:
            conditions.append(WorkflowRunRecord.workflow_name == workflow_name)
        if status:
            conditions.append(WorkflowRunRecord.status == status)

        # 计数查询
        count_stmt = select(func.count()).select_from(WorkflowRunRecord)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # 数据查询
        stmt = (
            select(WorkflowRunRecord)
            .order_by(desc(WorkflowRunRecord.created_at))
            .limit(limit)
            .offset(offset)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        records = result.scalars().all()

        return {
            "runs": [
                {
                    "id": r.id,
                    "workflow_name": r.workflow_name,
                    "status": r.status,
                    "thread_id": r.thread_id,
                    "result": r.result,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in records
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def get_run_detail(run_id: str) -> dict | None:
    """获取 run 详情，包含完整事件流。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        # 查询 run
        run_stmt = select(WorkflowRunRecord).where(WorkflowRunRecord.id == run_id)
        run_result = await session.execute(run_stmt)
        run_record = run_result.scalar_one_or_none()

        if not run_record:
            return None

        # 查询事件
        event_stmt = (
            select(WorkflowEventRecord)
            .where(WorkflowEventRecord.workflow_id == run_id)
            .order_by(WorkflowEventRecord.sequence)
        )
        event_result = await session.execute(event_stmt)
        event_records = event_result.scalars().all()

        return {
            "run": {
                "id": run_record.id,
                "workflow_name": run_record.workflow_name,
                "status": run_record.status,
                "thread_id": run_record.thread_id,
                "input_data": run_record.input_data,
                "result": run_record.result,
                "error": run_record.error,
                "created_at": run_record.created_at.isoformat() if run_record.created_at else None,
                "completed_at": run_record.completed_at.isoformat() if run_record.completed_at else None,
            },
            "events": [
                {
                    "id": e.id,
                    "sequence": e.sequence,
                    "category": e.category,
                    "kind": e.kind,
                    "source": e.source,
                    "payload": e.payload,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in event_records
            ],
        }


async def get_run_events(
    run_id: str,
    last_sequence: int = 0,
    limit: int = 100,
) -> list[dict]:
    """获取 run 的事件（支持分页）。"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(WorkflowEventRecord)
            .where(
                and_(
                    WorkflowEventRecord.workflow_id == run_id,
                    WorkflowEventRecord.sequence > last_sequence,
                )
            )
            .order_by(WorkflowEventRecord.sequence)
            .limit(limit)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "id": e.id,
                "sequence": e.sequence,
                "category": e.category,
                "kind": e.kind,
                "source": e.source,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in records
        ]


async def replay_events(
    run_id: str,
    from_sequence: int = 0,
    to_sequence: int | None = None,
) -> list[dict]:
    """Event Replay：从指定 sequence 开始重放事件。

    Args:
        run_id: Workflow Run ID
        from_sequence: 起始序列号（包含）
        to_sequence: 结束序列号（包含），None 表示重放到最后

    Returns:
        事件列表（按 sequence 排序）
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        conditions = [
            WorkflowEventRecord.workflow_id == run_id,
            WorkflowEventRecord.sequence >= from_sequence,
        ]
        if to_sequence is not None:
            conditions.append(WorkflowEventRecord.sequence <= to_sequence)

        stmt = (
            select(WorkflowEventRecord)
            .where(and_(*conditions))
            .order_by(WorkflowEventRecord.sequence)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "sequence": e.sequence,
                "category": e.category,
                "kind": e.kind,
                "source": e.source,
                "payload": e.payload,
            }
            for e in records
        ]


async def get_statistics(
    workflow_name: str | None = None,
    days: int = 7,
) -> dict:
    """获取统计信息。

    Args:
        workflow_name: 可选，按 workflow 过滤
        days: 统计天数

    Returns:
        {
            "total_runs": 100,
            "completed_runs": 90,
            "failed_runs": 5,
            "pending_runs": 5,
            "avg_duration_seconds": 120,
            "runs_by_day": [...],
        }
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        since = datetime.now() - timedelta(days=days)

        # 基础统计
        conditions = [WorkflowRunRecord.created_at >= since]
        if workflow_name:
            conditions.append(WorkflowRunRecord.workflow_name == workflow_name)

        # 计数
        count_stmt = select(func.count()).select_from(WorkflowRunRecord)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total_result = await session.execute(count_stmt)
        total_runs = total_result.scalar() or 0

        # 状态分布
        status_stmt = (
            select(WorkflowRunRecord.status, func.count())
            .where(and_(*conditions))
            .group_by(WorkflowRunRecord.status)
        )
        status_result = await session.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        return {
            "total_runs": total_runs,
            "completed_runs": status_counts.get("completed", 0),
            "failed_runs": status_counts.get("failed", 0),
            "running_runs": status_counts.get("running", 0),
            "pending_runs": status_counts.get("pending", 0),
            "period_days": days,
        }
